# coding=utf-8
import secrets
import os

from aiohttp import BodyPartReader
from PIL import Image

import config


class FileManager:

    filepath = './images/'
    if not os.path.exists(filepath):
        os.makedirs(filepath)

    support_images = ['jpeg', 'jpg', 'bmp', 'png']
    support_files = support_images

    @staticmethod
    def _file_token_generate(n_bytes: int = config.FILE_TOKEN_LENGTH) -> str:
        return secrets.token_urlsafe(n_bytes)

    @staticmethod
    async def filestream_save(field: BodyPartReader) -> str:
        file_format: str = field.filename.split(".")[-1]
        filename = f"{FileManager._file_token_generate()}.{file_format}"
        with open(FileManager.filepath + filename, 'wb') as f:
            while True:
                chunk = await field.read_chunk()  # 8192 bytes by default.
                if not chunk:
                    break
                f.write(chunk)
        return filename

    @staticmethod
    def image_compression(image_ref: str, size: int = 90, compression: int = config.FILE_IMAGE_COMPRESSION) -> None:
        original_image = Image.open(FileManager.filepath + image_ref)
        width, height = original_image.size
        if width > 10000 or height > 10000:
            original_image = original_image.resize(size)
        quality = 100 - compression
        original_image.save(FileManager.filepath + image_ref, "JPEG", quality=quality, optimize=True)
