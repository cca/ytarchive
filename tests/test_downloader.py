"""Tests for video downloader."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ytarchive.downloader import VideoDownloader
from ytarchive.models import ArchiveManifest, Video, VideoSnippet


def test_downloader_init():
    """Test VideoDownloader initialization."""
    downloader = VideoDownloader(
        output_dir="test-archive",
        quality="720p",
        skip_existing=True,
    )
    assert downloader.output_dir == Path("test-archive")
    assert downloader.quality == "720p"
    assert downloader.skip_existing is True


def test_downloader_creates_output_dir(tmp_path):
    """Test VideoDownloader creates output directory if it doesn't exist."""
    output_dir = tmp_path / "new-archive"
    downloader = VideoDownloader(str(output_dir))

    # Directory should be created
    assert output_dir.exists()
    assert output_dir.is_dir()


def test_skip_existing_returns_early(tmp_path):
    """Test skip_existing returns existing manifest without re-downloading."""
    # Create existing video directory with manifest
    video_id = "test123"
    video_dir = tmp_path / video_id
    video_dir.mkdir()

    # Create manifest
    existing_manifest = ArchiveManifest(
        video_id=video_id,
        title="Existing Video",
        archived_at=datetime.now(timezone.utc),
        metadata_file=str(video_dir / "metadata.json"),
    )
    manifest_path = video_dir / "manifest.json"
    manifest_path.write_text(existing_manifest.model_dump_json())

    # Create a test video to satisfy skip check
    (video_dir / "video.mp4").write_text("fake video")

    # Create downloader with skip_existing=True
    downloader = VideoDownloader(str(tmp_path), skip_existing=True)

    # Create a mock video
    mock_video = Video(
        id=video_id,
        snippet=VideoSnippet(
            publishedAt=datetime.now(timezone.utc).isoformat(),
            channelId="UC123",
            title="Existing Video",
            description="Test",
            thumbnails={},
            channelTitle="Test Channel",
            categoryId="22",
        ),
    )

    # Archive should return existing manifest without downloading
    result = downloader.archive_video(mock_video)

    assert result.video_id == video_id
    assert result.title == "Existing Video"


def test_manifest_creation(tmp_path):
    """Test manifest is created with correct structure."""
    video_id = "test123"
    title = "Test Video"
    video_dir = tmp_path / video_id
    video_dir.mkdir()

    manifest = ArchiveManifest(
        video_id=video_id,
        title=title,
        archived_at=datetime.now(timezone.utc),
        metadata_file=str(video_dir / "metadata.json"),
        video_file=str(video_dir / "video.mp4"),
        thumbnail_file=str(video_dir / "thumbnail.jpg"),
        caption_files={"en": str(video_dir / "captions.en.vtt")},
    )

    # Save manifest
    manifest_path = video_dir / "manifest.json"
    manifest_path.write_text(manifest.model_dump_json())

    # Verify it was saved
    assert manifest_path.exists()

    # Load and verify
    loaded = ArchiveManifest.model_validate_json(manifest_path.read_text())
    assert loaded.video_id == video_id
    assert loaded.title == title
    assert "en" in loaded.caption_files


def test_progress_hook():
    """Test progress hook is called during download."""
    downloader = VideoDownloader("test-archive")

    # Create a mock download status
    status = {
        "status": "downloading",
        "downloaded_bytes": 1024000,
        "total_bytes": 10240000,
    }

    # Call progress hook (should not raise)
    downloader._progress_hook(status)

    # Test with finished status
    finished = {
        "status": "finished",
    }
    downloader._progress_hook(finished)
