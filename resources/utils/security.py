# coding=utf-8
import string
import secrets
import hashlib


def build_password(length: int = 8):
    alphabet = f'{string.ascii_letters}{string.digits}'
    return "".join(secrets.choice(alphabet) for i in range(length))


def create_hash(str_: str):
    return hashlib.sha512(string=str_.encode('utf-8')).hexdigest()


__all__ = ['create_hash', 'build_password']
