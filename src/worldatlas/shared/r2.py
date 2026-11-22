"""Read and write R2 objects without exposing S3 request and response formats."""

from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from typing import IO

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError
from botocore.response import StreamingBody

DEFAULT_R2_ENDPOINT = (
    "https://8551d6a44afbf7d8080fb67cefe241fc.r2.cloudflarestorage.com"
)


class R2ObjectMissing(FileNotFoundError):
    """An R2 object does not exist at the requested key."""


@dataclass(frozen=True)
class R2Object:
    """An open object body with its byte count and HTTP metadata."""

    body: StreamingBody
    size_bytes: int | None
    content_type: str | None
    content_encoding: str | None


class R2Client:
    """Operate on R2 objects using bucket names and object keys."""

    def __init__(self, client: BaseClient) -> None:
        """Keep the underlying connection for this client's lifetime.

        Args:
            client: S3 client connected to an R2 account.
        """
        self._client = client

    def close(self) -> None:
        """Close the client's network connections."""
        self._client.close()

    @contextmanager
    def open(self, bucket: str, key: str) -> Iterator[R2Object]:
        """Open an object for streaming and close its body at the end of the block.

        Args:
            bucket: Bucket containing the object.
            key: Exact object key.

        Yields:
            The open binary stream and any returned byte count and HTTP metadata.

        Raises:
            R2ObjectMissing: The key does not exist.
        """
        try:
            response = self._client.get_object(Bucket=bucket, Key=key)
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "NoSuchKey":
                raise
            raise R2ObjectMissing(f"R2 object does not exist: {bucket}/{key}") from exc
        with closing(response["Body"]) as body:
            yield R2Object(
                body,
                response.get("ContentLength"),
                response.get("ContentType"),
                response.get("ContentEncoding"),
            )

    def put(
        self,
        bucket: str,
        key: str,
        body: bytes | IO[bytes],
        *,
        content_type: str,
        expected_etag: str | None,
        cache_control: str | None = None,
    ) -> None:
        """Write an object only if it has the expected ETag or is still absent.

        Args:
            bucket: Destination bucket.
            key: Exact destination key.
            body: Bytes or an open binary file to upload.
            content_type: HTTP media type to store.
            expected_etag: ETag to replace, or None to require an empty key.
            cache_control: Optional HTTP cache directive.

        Raises:
            ClientError: R2 rejects the request or a write condition fails.
        """
        options = (
            {"IfNoneMatch": "*"}
            if expected_etag is None
            else {"IfMatch": expected_etag}
        )
        if cache_control is not None:
            options["CacheControl"] = cache_control
        self._client.put_object(
            Bucket=bucket, Key=key, Body=body, ContentType=content_type, **options
        )

    def put_if_missing(
        self, bucket: str, key: str, body: bytes | IO[bytes], *, content_type: str
    ) -> None:
        """Upload an object while leaving any existing bytes in place.

        Args:
            bucket: Destination bucket.
            key: Exact destination key.
            body: Bytes or an open binary file to upload.
            content_type: HTTP media type to store.

        Raises:
            ClientError: R2 rejects the upload for a reason other than a failed
                write condition.
        """
        try:
            self.put(bucket, key, body, content_type=content_type, expected_etag=None)
        except ClientError as exc:
            if exc.response["ResponseMetadata"]["HTTPStatusCode"] != 412:
                raise

    def etag(self, bucket: str, key: str) -> str | None:
        """Read the current ETag without downloading the object.

        Args:
            bucket: Bucket containing the object.
            key: Exact object key.

        Returns:
            The ETag including its quotes, or None if the key does not exist.
        """
        try:
            return self._client.head_object(Bucket=bucket, Key=key)["ETag"]
        except ClientError as exc:
            if exc.response["ResponseMetadata"]["HTTPStatusCode"] != 404:
                raise
            return None

    def has_objects(self, bucket: str, prefix: str) -> bool:
        """Check whether an object has the given key prefix.

        Args:
            bucket: Bucket to search.
            prefix: Leading part of the object keys to match.

        Returns:
            True if any matching object exists.
        """
        page = self._client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1)
        return bool(page.get("Contents") or page.get("IsTruncated"))

    def list_keys(self, bucket: str, prefix: str) -> list[str]:
        """List object keys, including objects in nested folders.

        Args:
            bucket: Bucket to search.
            prefix: Leading part of the object keys to match.

        Returns:
            All matching object keys.
        """
        pages = self._client.get_paginator("list_objects_v2")
        return [
            item["Key"]
            for page in pages.paginate(Bucket=bucket, Prefix=prefix)
            for item in page.get("Contents", ())
        ]

    def list_folders(self, bucket: str, prefix: str) -> list[str]:
        """List the immediate folder prefixes under a key prefix.

        Args:
            bucket: Bucket to search.
            prefix: Leading part of the folder names to match.

        Returns:
            Matching prefixes including their trailing slash.
        """
        pages = self._client.get_paginator("list_objects_v2")
        return [
            item["Prefix"]
            for page in pages.paginate(Bucket=bucket, Prefix=prefix, Delimiter="/")
            for item in page.get("CommonPrefixes", ())
        ]

    def delete(self, bucket: str, key: str) -> None:
        """Delete the object at one key.

        Args:
            bucket: Bucket containing the object.
            key: Exact object key.
        """
        self._client.delete_object(Bucket=bucket, Key=key)


def make_r2_client() -> R2Client:
    """Open a client for the project's R2 account using the configured credentials.

    Returns:
        Client whose network connections the caller closes after use.
    """
    return R2Client(
        boto3.client('s3', endpoint_url=DEFAULT_R2_ENDPOINT, region_name='auto')
    )
