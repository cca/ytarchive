"""S3 uploader for archiving videos to AWS S3."""

import hashlib
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from rich.console import Console

console = Console()


class S3Uploader:
    """Upload archived videos to S3 with verification and cleanup."""

    def __init__(
        self,
        bucket: str | None = None,
        prefix: str = "",
        storage_class: str = "GLACIER_IR",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
    ):
        """Initialize S3 uploader.

        Args:
            bucket: S3 bucket name (defaults to S3_BUCKET env var)
            prefix: S3 key prefix (defaults to S3_PREFIX env var or empty)
            storage_class: S3 storage class (default: GLACIER_IR for long-term archival)
            aws_access_key_id: AWS access key (defaults to AWS_ACCESS_KEY_ID env var)
            aws_secret_access_key: AWS secret key (defaults to AWS_SECRET_ACCESS_KEY env var)
        """
        self.bucket = bucket or os.getenv("S3_BUCKET")
        if not self.bucket:
            raise ValueError("S3 bucket must be provided or set via S3_BUCKET environment variable")

        self.prefix = prefix or os.getenv("S3_PREFIX", "")
        if self.prefix and not self.prefix.endswith("/"):
            self.prefix += "/"

        self.storage_class = storage_class

        # Initialize boto3 client with explicit credentials or default credential chain
        session_kwargs = {}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs = {
                "aws_access_key_id": aws_access_key_id,
                "aws_secret_access_key": aws_secret_access_key,
            }
        elif os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
            session_kwargs = {
                "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
                "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
            }

        self.s3 = boto3.client("s3", **session_kwargs)
        console.print(f"[green]✓[/green] S3 uploader initialized (bucket: {self.bucket})")

    def _calculate_md5(self, file_path: Path) -> str:
        """Calculate MD5 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            MD5 hash as hex string
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def upload_file(self, local_path: Path, s3_key: str) -> dict[str, str]:
        """Upload a single file to S3 with verification.

        Args:
            local_path: Local file path
            s3_key: S3 key (path in bucket)

        Returns:
            Dictionary with upload metadata (key, etag, size, md5)

        Raises:
            Exception if upload fails or verification fails
        """
        if not local_path.exists():
            raise FileNotFoundError(f"File not found: {local_path}")

        # Calculate local MD5
        local_md5 = self._calculate_md5(local_path)
        file_size = local_path.stat().st_size

        # Upload to S3
        full_key = f"{self.prefix}{s3_key}"
        try:
            self.s3.upload_file(
                str(local_path),
                self.bucket,
                full_key,
                ExtraArgs={
                    "StorageClass": self.storage_class,
                    "Metadata": {"md5": local_md5},
                },
            )

            # Verify upload
            response = self.s3.head_object(Bucket=self.bucket, Key=full_key)
            etag = response["ETag"].strip('"')

            return {
                "key": full_key,
                "etag": etag,
                "size": file_size,
                "md5": local_md5,
            }
        except ClientError as e:
            raise Exception(f"Failed to upload {local_path.name}: {e}") from e

    def upload_directory(self, video_dir: Path, video_id: str) -> dict[str, dict]:
        """Upload entire video directory to S3.

        Uploads all files in the video directory:
        - video.mp4 (or other extension)
        - metadata.json
        - manifest.json
        - thumbnail.*
        - captions.*.vtt

        Args:
            video_dir: Local directory containing video files
            video_id: YouTube video ID (used as S3 key prefix)

        Returns:
            Dictionary mapping filename to upload metadata
        """
        if not video_dir.exists():
            raise FileNotFoundError(f"Directory not found: {video_dir}")

        console.print(f"\n[cyan]Uploading to S3:[/cyan] {video_id}")

        uploaded_files = {}
        s3_key_prefix = f"{video_id}/"

        # Upload all files in directory
        for file_path in video_dir.iterdir():
            if file_path.is_file():
                s3_key = f"{s3_key_prefix}{file_path.name}"
                try:
                    metadata = self.upload_file(file_path, s3_key)
                    uploaded_files[file_path.name] = metadata
                    console.print(f"  [green]✓[/green] Uploaded {file_path.name}")
                except Exception as e:
                    console.print(f"  [red]✗[/red] Failed to upload {file_path.name}: {e}")
                    raise

        console.print(f"  [green]✓[/green] Uploaded {len(uploaded_files)} files to S3")
        return uploaded_files

    def verify_upload(self, s3_key: str, local_md5: str) -> bool:
        """Verify file in S3 matches local MD5.

        Args:
            s3_key: S3 key (path in bucket)
            local_md5: Expected MD5 hash

        Returns:
            True if verification succeeds, False otherwise
        """
        full_key = f"{self.prefix}{s3_key}"
        try:
            response = self.s3.head_object(Bucket=self.bucket, Key=full_key)
            s3_md5 = response.get("Metadata", {}).get("md5")

            if s3_md5 == local_md5:
                return True

            console.print(f"  [yellow]⚠[/yellow] MD5 mismatch for {s3_key}")
            return False
        except ClientError:
            return False

    def check_exists(self, video_id: str) -> bool:
        """Check if video already exists in S3.

        Args:
            video_id: YouTube video ID

        Returns:
            True if video directory exists in S3
        """
        s3_key_prefix = f"{self.prefix}{video_id}/"
        try:
            response = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=s3_key_prefix, MaxKeys=1)
            return response.get("KeyCount", 0) > 0
        except ClientError:
            return False

    def cleanup_local(self, video_dir: Path) -> None:
        """Delete local directory after successful S3 upload.

        Args:
            video_dir: Local directory to delete
        """
        if not video_dir.exists():
            return

        # Delete all files in directory
        for file_path in video_dir.iterdir():
            if file_path.is_file():
                file_path.unlink()

        # Delete directory
        video_dir.rmdir()
        console.print(f"  [green]✓[/green] Cleaned up local files")
