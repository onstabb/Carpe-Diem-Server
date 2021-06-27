# coding=utf-8
import typing

from aiohttp_session import Session
from aiohttp import web
from pydantic import BaseModel, validator, Field
from .db.models import Profile


class _BaseType(BaseModel):

    class Config:
        arbitrary_types_allowed = True


class ClientRequest(_BaseType):
    request: web.Request
    method: str
    user: typing.Optional[Profile]


RequestObj = typing.TypeVar('RequestObj', bound=ClientRequest)
RequestType = typing.Type[ClientRequest]


class ServerResponse(_BaseType):
    status: str
    comment: str = ""
    save_session: typing.Optional[Session] = None


ResponseObj = typing.TypeVar('ResponseObj', bound=ServerResponse)
AsyncHandler = typing.Callable[[RequestObj], typing.Awaitable[ResponseObj]]


class ServerMessage(_BaseType):
    pass


ServerMessageObj = typing.TypeVar('ServerMessageObj', bound=ServerMessage)
ServerMessageType = typing.Type[ServerMessage]


class STATUSES:
    OK = "OK"
    ERROR = "Error"


class HandlerFilter(_BaseType):
    handler: AsyncHandler
    token_validate: bool
    check_profile_filled: bool


HandlersDict = typing.Dict[RequestType, HandlerFilter]
