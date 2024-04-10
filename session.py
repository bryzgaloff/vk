import time

import requests

from .exceptions import VkAPIError
from .utils import json_iter_parse, remove_meaningless_args
from .auth import get_access_token

DEFAULT_API_VERSION = '5.81'


class Session(object):
    API_URL = 'https://api.vk.com/method/'

    def __init__(self, access_token=None, email=None, password=None,
                 app_id=None, scope='offline', timeout=30,
                 max_requests_per_seconds=3, max_token_requests=2,
                 **method_default_args):

        self._email = email
        self._password = password
        self._app_id = app_id
        self._scope = scope
        self._access_token = access_token

        self._timeout = timeout
        self._default_method_args = method_default_args
        self._default_method_args.setdefault('v', DEFAULT_API_VERSION)

        self.requests_session = requests.Session()
        self.requests_session.headers['Accept'] = 'application/json'
        self.requests_session.headers['Content-Type'] = \
            'application/x-www-form-urlencoded'

        self.requests_till_cool_down = self.max_requests_per_second = \
            max_requests_per_seconds
        self.cool_down_till = time.time()

        self.available_token_requests = max_token_requests

    def _request_access_token(self):
        if not self.available_token_requests:
            raise RuntimeError('Maximum token request retries has exceeded')
        assert self._email is not None and self._password is not None \
            and self._app_id is not None and self._scope is not None
        self._access_token = get_access_token(
            self._email, self._password, self._app_id, self._scope
        )

    def make_request(self, method_name, method_args):
        response = self.send_api_request(method_name, method_args)
        # TODO replace with something less exceptional
        response.raise_for_status()

        # possible: {'error': ...} or {'response': ...}
        for response_or_error in json_iter_parse(response.text):
            if 'response' in response_or_error:
                return response_or_error['response']

            elif 'error' in response_or_error:
                error_data = response_or_error['error']
                error = VkAPIError(error_data)

                if error.is_access_token_incorrect():
                    self._request_access_token()
                    return self.make_request(method_name, method_args)

                else:
                    raise error

    def send_api_request(self, method_name, explicit_method_args):
        method_url = self.API_URL + method_name

        raw_method_args = self._default_method_args.copy()
        raw_method_args.update(explicit_method_args)
        raw_method_args['access_token'] = self._access_token
        method_args = remove_meaningless_args(raw_method_args)

        if not self.requests_till_cool_down:
            t = time.time()
            if self.cool_down_till > t:
                time.sleep(self.cool_down_till - t)
            self.requests_till_cool_down = self.max_requests_per_second
        if self.requests_till_cool_down == self.max_requests_per_second:
            self.requests_till_cool_down = time.time() + 1
        self.requests_till_cool_down -= 1

        response = self.requests_session \
            .post(method_url, method_args, timeout=self._timeout)
        return response
