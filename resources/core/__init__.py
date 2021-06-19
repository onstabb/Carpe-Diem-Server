from aiohttp_session.cookie_storage import EncryptedCookieStorage

from .dispatcher import Dispatcher

from .client_session import ClSession
import config

_cookie = EncryptedCookieStorage(secret_key=config.COOKIE_SECRET_KEY, cookie_name=config.SESSION_COOKIE_NAME)
dp = Dispatcher(encrypted_cookie_storage=_cookie)
