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
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "YouTube video archival tool" in result.output


def test_list_help():
    """Test list command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--help"])
    assert result.exit_code == 0
    assert "channel-id" in result.output


def test_archive_help():
    """Test archive command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["archive", "--help"])
    assert result.exit_code == 0
    assert "output-dir" in result.output


def test_status_help():
    """Test status command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "--help"])
    assert result.exit_code == 0
    assert "channel-id" in result.output
    assert "progress" in result.output.lower()
