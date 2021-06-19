import typing
import random
from ipaddress import IPv4Address

from ..core import ClSession
import config

_URL = 'https://sms.ru/sms'
_base_param = {"api_id": config.SMS_API}


class _SmsCodeService:

    def __init__(self, test_mode: bool = False):
        self._storage: typing.Dict[int, int] = {}   # code: mobile
        self._test = test_mode

    @staticmethod
    def __generate_code(length: int = config.SMS_CODE_LEN) -> int:
        from_ = 1 * 10**(length-1)
        to_ = (from_ * 10) - 1
        return random.randint(from_, to_)

    async def _accept_code(self, mobile: int) -> int:
        code = self.__generate_code()
        self._storage.update({code: mobile})
        return code

    async def _send_sms(self, mobile: int, text: str, ip: typing.Optional[IPv4Address] = None) -> dict:
        param = _base_param.copy()
        param.update(to=mobile, msg=text, json=1)

        if ip:
            param['ip'] = ip.compressed

        session = await ClSession.get_instance()
        async with session.post(f'{_URL}/send', data=param) as resp:

            assert resp.status == 200
            response_data = await resp.json()

        return response_data

    async def send_sms_code(self, to_mobile: int, ip: typing.Optional[IPv4Address] = None):
        code = await self._accept_code(to_mobile)
        msg = f'Carpe Diem Service. Your code: {code}'
        if self._test:
            with open('code', 'w') as file_code:
                file_code.write(str(code))
        else:
            await self._send_sms(to_mobile, msg, ip)

    async def storage_pop(self, code: int):
        return self._storage.pop(code, 0)

    async def sms_status(self, sms_id: str) -> dict:
        param = _base_param.copy()
        param.update(sms_id=sms_id, json=1)
        session = await ClSession.get_instance()
        async with session.post(f'{_URL}/status', data=param) as resp:
            assert resp.status == 200
            response_data = await resp.json()

        return response_data

