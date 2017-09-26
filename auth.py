import http.cookiejar
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urlparse

from vk.utils import split_key_value


def get_access_token(email, password, app_id, scope):
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
        urllib.request.HTTPRedirectHandler()
    )
    doc, url = auth_user(email, password, app_id, scope, opener)
    if urlparse(url).path != '/blank.html':
        # Need to give access to requested scope
        url = give_access(doc, opener)
    if urlparse(url).path != '/blank.html':
        raise RuntimeError(
            'Success has been expected, possibly incorrect login/password'
        )
    answer = dict(
        split_key_value(kv_pair)
        for kv_pair in urlparse(url).fragment.split('&')
    )
    if 'access_token' not in answer or 'user_id' not in answer:
        raise RuntimeError('Missing some values in answer')
    return answer['access_token']


class FormParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.url = None
        self.params = {}
        self.in_form = False
        self.form_parsed = False
        self.method = 'GET'

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == 'form':
            if self.form_parsed:
                raise RuntimeError('Second form on page')
            if self.in_form:
                raise RuntimeError('Already in form')
            self.in_form = True
        if not self.in_form:
            return
        attrs = dict((name.lower(), value) for name, value in attrs)
        if tag == 'form':
            self.url = attrs['action']
            if 'method' in attrs:
                self.method = attrs['method'].upper()
        elif tag == 'input' and 'type' in attrs and 'name' in attrs:
            if attrs['type'] in ['hidden', 'text', 'password']:
                self.params[attrs['name']] = \
                    attrs['value'] if 'value' in attrs else ''

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == 'form':
            if not self.in_form:
                raise RuntimeError('Unexpected end of <form>')
            self.in_form = False
            self.form_parsed = True


# Authorization form
def auth_user(email, password, app_id, scope, opener):
    response = opener.open(
        'http://oauth.vk.com/oauth/authorize?display=wap&'
        'redirect_uri=http://oauth.vk.com/blank.html&response_type=token&'
        'client_id={app_id}&scope={scope}'
        .format(app_id=app_id, scope=scope)
    )
    doc = response.read()
    parser = FormParser()
    parser.feed(str(doc))
    parser.close()
    assert parser.form_parsed and parser.url is not None \
        and 'pass' in parser.params and 'email' in parser.params
    parser.params['email'] = email
    parser.params['pass'] = password
    if parser.method == 'POST':
        response = opener.open(
            parser.url,
            urllib.parse.urlencode(parser.params).encode()
        )
    else:
        raise NotImplementedError('Method "{}"'.format(parser.method))
    return response.read(), response.geturl()


# Permission request form
def give_access(doc, opener):
    parser = FormParser()
    parser.feed(str(doc))
    parser.close()
    if not parser.form_parsed or parser.url is None:
        raise RuntimeError('Something wrong')
    if parser.method == 'POST':
        response = opener.open(
            parser.url,
            urllib.parse.urlencode(parser.params).encode()
        )
    else:
        raise NotImplementedError('Method "{}"'.format(parser.method))
    return response.geturl()
