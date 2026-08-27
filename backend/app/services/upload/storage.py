"""OutputStorage: upload rendered clips to S3/R2 so Instagram can pull them by URL."""
from __future__ import annotations

import boto3

from app.config import get_settings

settings = get_settings()


def upload_public(clip_path: str, key: str) -> str:
    """Upload clip to object storage; return public URL (needed for IG pull-from-URL)."""
    client = boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
    )
    client.upload_file(clip_path, settings.S3_BUCKET, key)
    return f"{settings.PUBLIC_BASE_URL}/{key}"
