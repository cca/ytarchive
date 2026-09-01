"""Tests for CLI commands."""

from click.testing import CliRunner

from ytarchive.cli import cli


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

    assert result.exit_code != 0
    assert "archive/UC123.json" in result.output
    assert "Must provide either --channel-id or --input-file" not in result.output
