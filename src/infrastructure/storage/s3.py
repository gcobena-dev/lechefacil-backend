from __future__ import annotations

from dataclasses import dataclass

import boto3

from src.infrastructure.storage.ports import PresignedUpload, StorageService


@dataclass(slots=True)
class S3StorageService(StorageService):
    bucket: str
    region: str
    prefix: str = ""
    public_url_base: str | None = None
    signed_url_expires: int = 600

    def __post_init__(self) -> None:
        self._s3 = boto3.client("s3", region_name=self.region)

    async def get_presigned_upload(
        self, key: str, content_type: str, *, expires_seconds: int = 600
    ) -> PresignedUpload:
        full_key = f"{self.prefix}{key}" if self.prefix else key
        conditions = [
            {"bucket": self.bucket},
            ["starts-with", "$key", full_key.rsplit("/", 1)[0] + "/"],
            {"Content-Type": content_type},
        ]
        fields = {"Content-Type": content_type}
        post = self._s3.generate_presigned_post(
            Bucket=self.bucket,
            Key=full_key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=expires_seconds or self.signed_url_expires,
        )
        return PresignedUpload(upload_url=post["url"], storage_key=full_key, fields=post["fields"])

    async def get_public_url(self, key: str) -> str:
        full_key = f"{self.prefix}{key}" if self.prefix and not key.startswith(self.prefix) else key
        if self.public_url_base:
            base = self.public_url_base.rstrip("/")
            return f"{base}/{full_key}"
        # default AWS URL
        if self.region == "us-east-1":
            return f"https://{self.bucket}.s3.amazonaws.com/{full_key}"
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{full_key}"

    async def put_object(self, key: str, data: bytes, content_type: str) -> None:
        full_key = f"{self.prefix}{key}" if self.prefix else key
        self._s3.put_object(Bucket=self.bucket, Key=full_key, Body=data, ContentType=content_type)
