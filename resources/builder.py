# coding=utf-8
import mongoengine
from aiohttp import web
from aiohttp_session import setup

from .handlers import dp
from .core.client_session import ClSession
import config


async def _on_startup(app: web.Application):
    mongoengine.connect(db=config.DB_NAME, host=config.DB_HOST, tlsAllowInvalidCertificates=True, ssl=True)


async def _on_shutdown(app: web.Application):
    mongoengine.disconnect_all()
    await ClSession.close()


async def build_app(**kwargs):
    app = web.Application(loop=kwargs.get('loop'))
    setup(app, dp.cookie_storage)
    app.on_startup.append(_on_startup)

    app.add_routes([web.post('/API', dp.process_request)])
    app.on_cleanup.append(_on_shutdown)
    return app

