import asyncio

from aiohttp import web

import config
from resources import build_app

loop = asyncio.get_event_loop()
app = loop.run_until_complete(build_app())

if __name__ == '__main__':
    web.run_app(app, host=config.SERVER_HOST, port=config.SERVER_PORT)