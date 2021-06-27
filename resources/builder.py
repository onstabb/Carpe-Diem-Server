# coding=utf-8
import pathlib

import mongoengine
from aiohttp import web
from aiohttp_session import setup

from .handlers import dp
from .core.utils import FileManager
from .core.client_session import ClSession
import config


async def _on_startup(app: web.Application):
    mongoengine.connect(db=config.DB_NAME, host=config.DB_HOST, tlsAllowInvalidCertificates=True, ssl=True)


async def _on_shutdown(app: web.Application):
    mongoengine.disconnect_all()
    await ClSession.close()
    await dp.websockets_close()


async def build_app(**kwargs):
    app = web.Application(loop=kwargs.get('loop'))
    setup(app, dp.cookie_storage)
    app.on_startup.append(_on_startup)
    current_working_path: str = str(pathlib.Path().absolute().as_posix())
    images_path = FileManager.filepath[1:]
    app.add_routes([
        web.post(config.ROUTE_API, dp.process_request),
        web.get(config.ROUTE_WS, dp.process_ws),
        web.static(config.STATIC_FILES_PATH, f'{current_working_path}{images_path}', show_index=True)
    ])
    app.on_cleanup.append(_on_shutdown)
    return app

