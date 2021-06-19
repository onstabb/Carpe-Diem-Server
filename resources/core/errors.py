# coding=utf-8
class BaseServerException(Exception):
    pass


class InvalidRequest(BaseServerException):
    pass


class InvalidMethod(BaseServerException):
    pass


class InvalidToken(BaseServerException):
    pass


class InvalidRequestData(BaseServerException):
    pass


class FileNotSupport(BaseServerException):
    pass
