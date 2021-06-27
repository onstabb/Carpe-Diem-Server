# coding=utf-8
from ..core.types import ServerResponse


class NewUserRegistered(ServerResponse):
    new_password: str = None


class SelectedProfile(ServerResponse):
    id: int
    name: str
    age: int
    gender: str
    preferred_gender: str
    description: str
    city: str
    photo: str
