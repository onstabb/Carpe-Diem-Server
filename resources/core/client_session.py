from aiohttp import ClientSession


class ClSession:

    __client: ClientSession = None

    @classmethod
    async def get_instance(cls) -> ClientSession:
        if not cls.__client or cls.__client.closed:
            cls.__client = ClientSession()
        return cls.__client

    @classmethod
    async def close(cls) -> None:
        if cls.__client and not cls.__client.closed:
            await cls.__client.close()
