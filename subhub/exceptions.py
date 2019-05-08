class SubHubError(Exception):
    """Base SubHub Exception"""
    status_code = 500


class IntermittentError(SubHubError):
    status_code = 503

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class ClientError(SubHubError):
    status_code = 400

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class ServerError(SubHubError):
    status_code = 500

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code
