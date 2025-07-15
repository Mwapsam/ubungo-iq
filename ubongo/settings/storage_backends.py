from storages.backends.s3boto3 import S3Boto3Storage
from django.utils.module_loading import import_string


class StaticToS3Storage(S3Boto3Storage):
    location = "static"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.local_storage = import_string("compressor.storage.CompressorFileStorage")()

    def save(self, name, content):
        filename = super().save(name, content)
        try:
            self.local_storage.save(name, content)
        except FileExistsError:
            pass
        return filename


class mediaRootS3Boto3Storage(S3Boto3Storage):
    location = "media"
    file_overwrite = False
