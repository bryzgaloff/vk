class VkException(Exception):
    pass


class VkAPIError(VkException):
    __slots__ = ('error', 'code', 'message', 'redirect_uri')

    AUTHORIZATION_FAILED = 5

    def __init__(self, error_data):
        super(VkAPIError, self).__init__()
        self.error_data = error_data
        self.code = error_data.get('error_code')
        self.message = error_data.get('error_msg')
        self.redirect_uri = error_data.get('redirect_uri')

    @property
    def pretty_request_params(self):
        request_params = self.error_data.get('request_params')
        if not request_params:
            return None
        request_params_dict = {
            param['key']: param['value']
            for param in request_params
        }
        return request_params_dict

    def is_access_token_incorrect(self):
        return self.code == VkAPIError.AUTHORIZATION_FAILED

    def __str__(self):
        error_message = \
            '{self.code}. {self.message}. ' \
            'request_params = {self.pretty_request_params}'.format(self=self)
        if self.redirect_uri:
            error_message += \
                ',\nredirect_uri = "{self.redirect_uri}"'.format(self=self)
        return error_message
