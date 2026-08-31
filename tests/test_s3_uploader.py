"""Tests for S3 uploader."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ytarchive.s3_uploader import S3Uploader


def test_s3_uploader_init_with_bucket():
    """Test S3Uploader initialization with explicit bucket."""
    with patch("ytarchive.s3_uploader.boto3"):
        uploader = S3Uploader(bucket="test-bucket")
        assert uploader.bucket == "test-bucket"
        assert uploader.prefix == ""
        assert uploader.storage_class == "GLACIER_IR"


def test_s3_uploader_init_with_prefix():
    """Test S3Uploader initialization with prefix."""
    with patch("ytarchive.s3_uploader.boto3"):
        uploader = S3Uploader(bucket="test-bucket", prefix="videos")
        assert uploader.prefix == "videos/"


def test_s3_uploader_init_prefix_already_has_slash():
    """Test prefix normalization when it already ends with /."""
    with patch("ytarchive.s3_uploader.boto3"):
        uploader = S3Uploader(bucket="test-bucket", prefix="videos/")
        assert uploader.prefix == "videos/"


def test_s3_uploader_init_from_env_vars():
    """Test S3Uploader initialization from environment variables."""
    with patch.dict(
        os.environ,
        {
            "S3_BUCKET": "env-bucket",
            "S3_PREFIX": "env-prefix",
            "AWS_ACCESS_KEY_ID": "test-key",
            "AWS_SECRET_ACCESS_KEY": "test-secret",
        },
    ):
        with patch("ytarchive.s3_uploader.boto3") as mock_boto3:
            uploader = S3Uploader()
            assert uploader.bucket == "env-bucket"
            assert uploader.prefix == "env-prefix/"
            # Verify boto3 client was called with credentials
            mock_boto3.client.assert_called_once_with(
                "s3",
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret",
            )


def test_s3_uploader_init_missing_bucket():
    """Test S3Uploader raises error when bucket not provided."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="S3 bucket must be provided"):
            S3Uploader()


def test_s3_uploader_init_explicit_credentials():
    """Test S3Uploader with explicit credentials."""
    with patch("ytarchive.s3_uploader.boto3") as mock_boto3:
        uploader = S3Uploader(
            bucket="test-bucket",
            aws_access_key_id="explicit-key",
            aws_secret_access_key="explicit-secret",
        )
        mock_boto3.client.assert_called_once_with(
            "s3",
            aws_access_key_id="explicit-key",
            aws_secret_access_key="explicit-secret",
        )


def test_calculate_md5(tmp_path):
    """Test MD5 calculation."""
    with patch("ytarchive.s3_uploader.boto3"):
        uploader = S3Uploader(bucket="test-bucket")

        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        # Calculate MD5
        md5 = uploader._calculate_md5(test_file)

        # Known MD5 for "Hello, World!"
        expected_md5 = "65a8e27d8879283831b664bd8b7f0ad4"
        assert md5 == expected_md5


def test_upload_file_not_found():
    """Test upload_file raises error for non-existent file."""
    with patch("ytarchive.s3_uploader.boto3"):
        uploader = S3Uploader(bucket="test-bucket")

        with pytest.raises(FileNotFoundError):
            uploader.upload_file(Path("/nonexistent/file.txt"), "test.txt")


def test_upload_directory_not_found():
    """Test upload_directory raises error for non-existent directory."""
    with patch("ytarchive.s3_uploader.boto3"):
        uploader = S3Uploader(bucket="test-bucket")

        with pytest.raises(FileNotFoundError):
            uploader.upload_directory(Path("/nonexistent/dir"), "video123")


def test_cleanup_local(tmp_path):
    """Test cleanup_local deletes directory."""
    with patch("ytarchive.s3_uploader.boto3"):
        uploader = S3Uploader(bucket="test-bucket")

        # Create a test directory with files
        video_dir = tmp_path / "video123"
        video_dir.mkdir()
        (video_dir / "video.mp4").write_text("fake video")
        (video_dir / "metadata.json").write_text("{}")

        # Cleanup
        uploader.cleanup_local(video_dir)

        # Verify directory is deleted
        assert not video_dir.exists()


def test_cleanup_local_nonexistent_dir():
    """Test cleanup_local handles non-existent directory gracefully."""
    with patch("ytarchive.s3_uploader.boto3"):
        uploader = S3Uploader(bucket="test-bucket")

        # Should not raise error
        uploader.cleanup_local(Path("/nonexistent/dir"))
