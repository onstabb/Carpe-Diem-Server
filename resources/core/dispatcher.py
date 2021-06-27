import logging
import typing

from aiohttp import web, WSMessage, WSMsgType, MultipartReader
from aiohttp_session import get_session, cookie_storage, new_session
from pydantic import ValidationError

from .db import Profile, ServerMessage
from . import errors
from . import types
from .utils import FileManager
import config


class Dispatcher:
    _handlers: types.HandlersDict = {}
    log: logging.Logger = logging.getLogger("server")

    def __init__(self, encrypted_cookie_storage: cookie_storage.EncryptedCookieStorage):
        self.cookie_storage = encrypted_cookie_storage
        self._websockets: typing.Dict[int, web.WebSocketResponse] = {}

    async def websockets_close(self):
        for ws in self._websockets.values():
            await ws.close()

    def __get_method_type(self, method_name: typing.AnyStr) -> typing.Union[types.RequestType, None]:
        for type_ in self._handlers:
            if type_.__name__ == method_name:
                return type_
        return None

    @staticmethod
    async def __get_user_from_session(
            request: web.Request, only_filled_profile: bool = False
    ) -> typing.Union[Profile, None]:
        session = await get_session(request)
        try:
            assert session.new is False
            user_id = session.get('user_id')
            assert user_id is not None
        except AssertionError:
            raise errors.InvalidToken("Invalid token")
        user = Profile.get_one(id_=user_id)
        if not user.is_filled and only_filled_profile:
            raise errors.FilledProfileOnly("This method can use only filled profiles")

        return user

    @staticmethod
    async def user_start_session(profile: Profile, request: web.Request):
        session = await new_session(request)
        session.update(user_id=profile.id_)
        return session

    async def __check_user_messages(self, user: Profile):
        for message in user.get_all_messages():
            data = ServerMessage(**message.message)
            await self.send_ws_message(user, sender=message.sender, data=data)

    async def __process_handler(
            self, handler: types.HandlerFilter, request_type: types.RequestType, data: dict
    ) -> types.RequestObj:
        try:
            method = request_type(**data)
        except ValidationError as e:
            raise errors.InvalidRequestData(e)
        except Exception as e:
            self.log.exception(e)
            raise errors.InvalidRequestData()

        try:
            result = await handler.handler(method)
        except Exception as e:
            self.log.exception(e)
            raise e

        return result

    async def _process_multipart_request(self, request: web.Request):
        try:
            reader: MultipartReader = await request.multipart()
        except AssertionError:  # if not multipart
            raise errors.InvalidRequest("Invalid request")

        field = await reader.next()
        if field.name != "method":
            raise errors.InvalidRequest("Multipart data must starts with field 'method'")

        method_name = (await field.read(decode=True)).decode(encoding='utf-8')

        method_type = self.__get_method_type(method_name)

        if not method_type:
            raise errors.InvalidMethod("Method doesn't exists")

        handler_obj = self._handlers[method_type]

        user = await self.__get_user_from_session(
            request=request, only_filled_profile=handler_obj.check_profile_filled
        ) if handler_obj.token_validate else None

        method_data = {"method": method_name, "request": request, "user": user}
        async for field_ in reader:
            if field_.filename:
                file_format: str = field_.filename.split('.')[-1]

                if file_format.lower() not in FileManager.support_files:
                    raise errors.FileNotSupport("This file is not supported")

                file_size: int = int(field_.headers.get('Content-Length'))
                if file_format.lower() in FileManager.support_images and file_size > config.FILE_IMAGE_MAX_SIZE:
                    raise errors.FileNotSupport("File is too large")

                value = await FileManager.filestream_save(field_)
            else:
                value = await field_.read()

            method_data[field_.name] = value
        return await self.__process_handler(handler=handler_obj, request_type=method_type, data=method_data)

    async def _process_json_request(self, request: web.Request):
        try:
            json_data: dict = await request.json()
            method_name = json_data['method']
        except KeyError:
            raise errors.InvalidRequest("Invalid request")

        json_data['request'] = request
        method_type = self.__get_method_type(method_name)
        if not method_type:
            raise errors.InvalidMethod("Method doesn't exists")

        handler_obj = self._handlers[method_type]
        user = await self.__get_user_from_session(
            request=request, only_filled_profile=handler_obj.check_profile_filled
        ) if handler_obj.token_validate else None

        json_data.update(user=user)

        return await self.__process_handler(handler=handler_obj, request_type=method_type, data=json_data)

    async def send_ws_message(
            self, profile: Profile, data: types.ServerMessageObj, sender: typing.Optional[Profile] = None
    ):
        ws: typing.Union[web.WebSocketResponse, None] = self._websockets.get(profile.id_)
        try:
            assert ws is not None
            prepared_data = {"type": data.__class__.__name__, "from": sender.id_ if sender else 0}
            prepared_data.update(data.dict())
            await ws.send_json(prepared_data)
        except (AssertionError, ):
            self._websockets.pop(profile.id_, None)
            message: ServerMessage = ServerMessage(sender=sender, recipient=profile, message=data.dict())
            message.save()

    async def process_ws(self, request: web.Request):
        ws: web.WebSocketResponse = web.WebSocketResponse()
        await ws.prepare(request)
        try:
            user: Profile = await self.__get_user_from_session(request, only_filled_profile=True)
            await self.__check_user_messages(user)
            self._websockets[user.id_] = ws
            async for msg in ws:
                msg: WSMessage
                if msg.type == WSMsgType.ERROR or msg.data == 'close':
                    await ws.close()
        except Exception as e:
            self.log.exception(e)
        finally:
            return ws

    async def process_request(self, request: web.Request):
        try:
            if request.content_type == 'multipart/form-data':
                proceed = await self._process_multipart_request(request)
            else:
                proceed = await self._process_json_request(request)
        except Exception as e:
            proceed = types.ServerResponse(status=types.STATUSES.ERROR, comment=str(e))
            if not issubclass(e.__class__, errors.BaseServerException):
                proceed.comment = "Internal server error"
                self.log.exception(e)

        data_to_send = proceed.dict()
        data_to_send.pop("save_session")
        response = web.json_response(data_to_send)
        if proceed.save_session:
            await self.cookie_storage.save_session(request=request, session=proceed.save_session, response=response)

        return response

    # @decorator
    def register_handler(
            self, request_type: types.RequestType, validate_token: bool = True, check_profile_filled: bool = False
    ) -> callable:
        def wrapper(callback: types.AsyncHandler):
            handler = types.HandlerFilter(
                handler=callback, token_validate=validate_token, check_profile_filled=check_profile_filled
            )
            self._handlers[request_type] = handler
            return callback

        return wrapper
