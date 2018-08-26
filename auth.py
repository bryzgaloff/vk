import http.cookiejar
import urllib.error
import urllib.error
import urllib.parse
import urllib.parse
import urllib.request
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urlparse


def get_access_token(email, password, client_id, scope):
    url_opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
        urllib.request.HTTPRedirectHandler()
    )
    doc, url = _auth_user(email, password, client_id, scope, url_opener)

    parsed_url = urlparse(url)
    if parsed_url.path != '/blank.html':
        # Have to approve access to requested scope
        url = _approve_access(doc, url_opener)

    parsed_url = urlparse(url)
    if parsed_url.path != '/blank.html':
        raise RuntimeError('Success has been expected')

    response = dict(
        _split_key_value_pair(kv_pair)
        for kv_pair in parsed_url.fragment.split('&')
    )
    if 'access_token' not in response or 'user_id' not in response:
        raise RuntimeError('Missing some values in response')

    return response['access_token']


# Authorization form
def _auth_user(email, password, client_id, scope, opener):
    if isinstance(scope, list):
        scope = ','.join(scope)
    assert isinstance(scope, str)

    response = opener.open(
        'http://oauth.vk.com/oauth/authorize?'
        'redirect_uri=http://oauth.vk.com/blank.html&response_type=token&'
        'client_id={}&scope={}&display=wap'.format(client_id, scope)
    )
    doc = response.read()

    parser = _FormParser()
    parser.feed(str(doc))
    parser.close()

    if not parser.parsed or parser.url is None \
            or 'pass' not in parser.params or 'email' not in parser.params:
        raise RuntimeError('Wrong form params')

    parser.params['email'] = email
    parser.params['pass'] = password

    if parser.method == 'POST':
        params_encoded = urllib.parse.urlencode(parser.params).encode()
        response = opener.open(parser.url, params_encoded)
    else:
        raise NotImplementedError('Method "%s"' % parser.method)

    return response.read(), response.geturl()


# Permission request form
def _approve_access(doc, opener):
    parser = _FormParser()
    parser.feed(str(doc))
    parser.close()
    if not parser.parsed or parser.url is None:
        raise RuntimeError('Something wrong')
    if parser.method == 'POST':
        params_encoded = urllib.parse.urlencode(parser.params).encode()
        response = opener.open(parser.url, params_encoded)
    else:
        raise NotImplementedError('Method "%s"' % parser.method)
    return response.geturl()


class _FormParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.url = None
        self.params = {}
        self.is_parsing = False
        self.parsed = False
        self.method = 'GET'

    def handle_starttag(self, tag, attributes):
        tag = tag.lower()
        if tag == 'form':
            if self.parsed:
                raise RuntimeError('Second form on page')
            if self.is_parsing:
                raise RuntimeError('Already in form')
            self.is_parsing = True
        if not self.is_parsing:
            return
        attr_dict = dict((name.lower(), value) for name, value in attributes)
        if tag == 'form':
            self.url = attr_dict['action']
            if 'method' in attr_dict:
                self.method = attr_dict['method'].upper()
        elif tag == 'input' and 'type' in attr_dict and 'name' in attr_dict:
            if attr_dict['type'] in ('hidden', 'text', 'password'):
                name = attr_dict['name']
                self.params[name] = attr_dict.get('value', '')

    def handle_endtag(self, tag):
        if tag.lower() == 'form':
            if not self.is_parsing:
                raise RuntimeError('Unexpected end of <form>')
            self.is_parsing = False
            self.parsed = True


def _split_key_value_pair(kv_pair):
    kv = kv_pair.split('=')
    return kv[0], kv[1]
