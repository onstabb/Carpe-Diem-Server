# coding=utf-8
import json
from typing import Optional

from pydantic import validator

from ..core.types import ClientRequest
from ..utils.geoAPI import LocationType


class TestRequest(ClientRequest):
    text: str


class Login(ClientRequest):
    mobile: int
    password: Optional[str] = None


class SmsCodeConfirmation(ClientRequest):
    code: int


class EditProfile(ClientRequest):
    name: str
    age: int
    gender: str
    preferred_gender: str
    description: str
    locality: LocationType
    photo: Optional[str] = None

    @validator("locality", pre=True)
    def _locality(cls, v: LocationType):
        if isinstance(v, str):
            try:
                coordinates = json.loads(v)
            except json.JSONDecodeError:
                return v

            return coordinates
        return v


class SelectProfile(ClientRequest):
    pass
