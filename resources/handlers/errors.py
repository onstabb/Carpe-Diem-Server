# coding=utf-8
from ..core.errors import *


class IncorrectPassword(BaseServerException):
    pass


class InvalidSmsCode(BaseServerException):
    pass
