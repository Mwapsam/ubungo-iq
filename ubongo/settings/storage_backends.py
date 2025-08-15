from storages.backends.s3boto3 import S3Boto3Storage
from django.utils.module_loading import import_string


class StaticToS3Storage(S3Boto3Storage):
    location = "static"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Disable compressor storage to prevent JavaScript dependency issues
        try:
            self.local_storage = import_string("django.core.files.storage.FileSystemStorage")()
        except Exception:
            self.local_storage = None

    def save(self, name, content):
        filename = super().save(name, content)
        if self.local_storage:
            try:
                self.local_storage.save(name, content)
            except FileExistsError:
                pass
        return filename


class mediaRootS3Boto3Storage(S3Boto3Storage):
    location = "media"
    file_overwrite = False
