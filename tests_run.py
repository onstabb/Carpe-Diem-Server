import unittest

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from aiohttp import ClientResponse

import config
from resources import builder


class AioChatTestCase(AioHTTPTestCase):
    """ Base test case for aiochat """

    URL = '/API'
    USER_MOBILE = 380975042095                      # Мобильный телефон тестового юзера
    TOKEN: str = None                               # Токен получаемый при регистрации в приложении

    async def get_application(self):
        return await builder.build_app()

    async def send_request(self, with_token: bool = False, send_as_json: bool = True, **kwargs) -> dict:
        cookies = {config.SESSION_COOKIE_NAME: self.TOKEN} if with_token else None
        if send_as_json:

            response: ClientResponse = await self.client.post(self.URL, json=kwargs, cookies=cookies)
        else:
            # file = FormData()
            # for key, value in kwargs.items():
            #     if key == "photo":
            #         file.add_field(name=key, value=value, filename=value.name)
            #     else:
            #         file.add_field(name=key, value=str(value))

            response: ClientResponse = await self.client.post(self.URL, data=kwargs, cookies=cookies)

        self.assertEqual(response.status, 200)
        content = await response.json()
        cookie = response.cookies.get(config.SESSION_COOKIE_NAME)
        if cookie:
            self.TOKEN = cookie.value
        return content


class IndexTestCase(AioChatTestCase):

    """ Testing app"""

    # Пример теста:
    @unittest_run_loop  # Добавляем декоратор
    async def test_request(self):   # Определяем функцию (ОБЯЗАТЕЛЬНО НАЗВАНИЕ ДОЛЖНО НАЧИНАТЬСЯ С "test_")
        data = {"method": "TestRequest", "text": "hi, pal, lol"}  # готовим json запрос
        content = await self.send_request(**data)  # отправляем запрос
        self.assertIn(data.get('text'), content.get('comment'))  # проверяем результат(можно чекнуть все "self.assert...")

    # пример отправки невалидных запросов на сервер
    @unittest_run_loop
    async def test_invalid_request(self):
        data = {"method": "InvalidRequest", "321text": "hi, pal, lol"}  # Несуществует метода "InvalidRequest"
        response = await self.send_request(**data)
        self.assertDictEqual({'status': 'Error', 'comment': "Method doesn't exists"}, response)
        data = {"method": "TestRequest", "321text": "hi, pal, lol"}     # Неккорентый параметр "321text"
        response = await self.send_request(**data)
        self.assertEqual(response.get("status"), "Error")

    # Это пример регистрации
    @unittest_run_loop
    async def test_registration(self):
        data = {"method": "Login", 'mobile': self.USER_MOBILE}  # Логинимся по своему мобильному номеру
        response = await self.send_request(**data)
        self.assertEqual(response.get("status"), "OK")        # Сервер должен прислать инфу что он отослал смс нам

        if not config.SMS_SERVICE_TEST_MODE:                  # От флага SMS_SERVICE_TEST_MODE зависит будет ли отправляться реальное СМС сообщение
            code = int(input('Input code for confirmation: '))
        else:
            with open('code', 'r') as f:                     # Если этот флаг False, то код придет в виде текстового безымянного файла
                code = int(f.read())
            self.assertIsInstance(code, int)                 # код должен быть числом

        data = {"method": "SmsCodeConfirmation", "code": code}         # Отправляем код на сервер
        response = await self.send_request(**data)
        self.assertIsInstance(self.TOKEN, str)                       # Получили токен
        self.assertIsInstance(response.get("new_password"), str)       # Проверяем ответ от сервера. Должен прийти новый пароль от аккаунта

        data = {"method": "SelectProfile"}
        response = await self.send_request(**data)
        self.assertEqual(response.get("status"), "Error")

        data = {
            "method": "EditProfile",
            "name": 'Vladyslav',
            'age': "22",
            'gender': "male",
            "preferred_gender": "any",
            "description": "I like cats, sushi, music, cinema. Searching for good friends.",
            'locality': "Wroclaw",
            'photo': open('test-photo.jpg', 'rb')
        }

        response = await self.send_request(**data, send_as_json=False, with_token=True)
        self.assertEqual(response.get("status"), "OK")


if __name__ == '__main__':
    unittest.main(verbosity=2)
