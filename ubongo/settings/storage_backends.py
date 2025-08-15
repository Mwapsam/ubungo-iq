from storages.backends.s3boto3 import S3Boto3Storage
from django.core.files.storage.handler import get_storage_class


class StaticToS3Storage(S3Boto3Storage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.local_storage = get_storage_class(
            "compressor.storage.CompressorFileStorage"
        )()

    def save(self, name, content):
        filename = super().save(name, content)
        try:
            self.local_storage._save(name, content)
        except FileExistsError:
            pass
        return filename


class mediaRootS3Boto3Storage(S3Boto3Storage):
    location = "media"
    file_overwrite = False


class CachedS3Boto3Storage(S3Boto3Storage):
    def __init__(self, *args, **kwargs):
        super(CachedS3Boto3Storage, self).__init__(*args, **kwargs)
        self.local_storage = get_storage_class(
            "compressor.storage.CompressorFileStorage"
        )()

    def save(self, filename, content):
        filename = super(CachedS3Boto3Storage, self).save(filename, content)
        self.local_storage._save(filename, content)
        return filename
