"""Tests for CLI commands."""

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from ytarchive.cli import cli
from ytarchive.models import ArchiveManifest, Video


def test_cli_version():
    """Test CLI version command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0


def test_cli_help():
    """Test CLI help command."""
    runner = CliRunner()
    for help_flag in ("-h", "--help"):
        result = runner.invoke(cli, [help_flag])
        assert result.exit_code == 0
        assert "YouTube video archival tool" in result.output


def test_list_help():
    """Test list command help."""
    runner = CliRunner()
    for help_flag in ("-h", "--help"):
        result = runner.invoke(cli, ["list", help_flag])
        assert result.exit_code == 0
        assert "channel-id" in result.output
        assert "CHANNEL" in result.output


def test_archive_help():
    """Test archive command help."""
    runner = CliRunner()
    for help_flag in ("-h", "--help"):
        result = runner.invoke(cli, ["archive", help_flag])
        assert result.exit_code == 0
        assert "output-dir" in result.output
        assert "CHANNEL" in result.output
        assert "--upload-to-s3" in result.output
        assert "--s3-bucket" in result.output
        assert "--s3-prefix" in result.output
        assert "--delete-after-upload" in result.output


def test_status_help():
    """Test status command help."""
    runner = CliRunner()
    for help_flag in ("-h", "--help"):
        result = runner.invoke(cli, ["status", help_flag])
        assert result.exit_code == 0
        assert "channel-id" in result.output
        assert "CHANNEL" in result.output
        assert "progress" in result.output.lower()
        assert "Example:" not in result.output


def test_status_uses_channel_environment_variable():
    """Test that status uses CHANNEL when --channel-id is omitted."""
    runner = CliRunner()
    result = runner.invoke(cli, ["status"], env={"CHANNEL": "UC123"})

    assert result.exit_code == 0
    assert "archive/UC123.json" in result.output
    assert "Must provide either --channel-id or --input-file" not in result.output


def test_status_reads_channel_archive_index(tmp_path):
    """Test status summarizes the channel-specific manifest index."""
    manifest = ArchiveManifest(
        video_id="video-1",
        title="Archived video",
        archived_at=datetime.now(UTC),
        metadata_file="archive/video-1/metadata.json",
        s3_uploaded=True,
    )
    index_path = tmp_path / "UC123.json"
    index_path.write_text(json.dumps([manifest.model_dump(mode="json")]))

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["status", "--channel-id", "UC123", "--output-dir", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "Downloaded:       1 (100.0%)" in result.output
    assert "Uploaded to S3:   1 (100.0%)" in result.output


def test_archive_applies_max_results_after_skipping_uploaded_videos(tmp_path):
    """Test max-results selects the next videos after prior S3 uploads."""
    videos = [
        Video.model_validate(
            {
                "id": f"video-{number}",
                "snippet": {
                    "publishedAt": "2026-01-01T00:00:00Z",
                    "channelId": "UC123",
                    "title": f"Video {number}",
                    "description": "",
                    "thumbnails": {},
                    "channelTitle": "Channel",
                    "categoryId": "22",
                },
            }
        )
        for number in range(1, 5)
    ]
    existing_manifests = [
        ArchiveManifest(
            video_id=video.id,
            title=video.snippet.title,
            archived_at=datetime.now(UTC),
            metadata_file=f"archive/{video.id}/metadata.json",
            s3_uploaded=True,
        )
        for video in videos[:2]
    ]
    index_path = tmp_path / "UC123.json"
    index_path.write_text(
        json.dumps(
            [manifest.model_dump(mode="json") for manifest in existing_manifests]
        )
    )
    client_secrets = tmp_path / "client_secrets.json"
    client_secrets.write_text("{}")

    client = MagicMock()
    client.resolve_channel_id.return_value = "UC123"
    client.get_channel_videos.return_value = videos
    downloader = MagicMock()
    downloader.archive_video.side_effect = [
        ArchiveManifest(
            video_id=video.id,
            title=video.snippet.title,
            archived_at=datetime.now(UTC),
            metadata_file=f"archive/{video.id}/metadata.json",
        )
        for video in videos[2:]
    ]

    with (
        patch("ytarchive.cli.YouTubeClient", return_value=client),
        patch("ytarchive.cli.VideoDownloader", return_value=downloader),
    ):
        result = CliRunner().invoke(
            cli,
            [
                "archive",
                "--channel-id",
                "UC123",
                "--max-results",
                "2",
                "--output-dir",
                str(tmp_path),
                "--client-secrets",
                str(client_secrets),
            ],
        )

    assert result.exit_code == 0
    client.get_channel_videos.assert_called_once_with("UC123")
    assert [call.args[0].id for call in downloader.archive_video.call_args_list] == [
        "video-3",
        "video-4",
    ]
    saved_index = json.loads(index_path.read_text())
    assert [item["video_id"] for item in saved_index] == [
        "video-1",
        "video-2",
        "video-3",
        "video-4",
    ]
