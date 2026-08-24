"""Command-line interface for ytarchive."""

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from ytarchive.downloader import VideoDownloader
from ytarchive.models import Video
from ytarchive.youtube_api import YouTubeClient

console = Console()


@click.group()
@click.version_option()
def cli():
    """YouTube video archival tool."""
    pass


@cli.command()
@click.option(
    "--channel-id",
    help="YouTube channel ID, username, or @handle",
)
@click.option(
    "--max-results",
    type=int,
    help="Maximum number of videos to retrieve",
)
@click.option(
    "--output",
    type=click.Path(),
    help="Save video list to JSON file",
)
@click.option(
    "--client-secrets",
    default="client_secrets.json",
    help="Path to OAuth client secrets file",
)
def list(channel_id: str, max_results: int | None, output: str | None, client_secrets: str):
    """List all videos from a YouTube channel."""
    if not channel_id:
        console.print("[red]Error: --channel-id is required[/red]")
        raise click.Abort()

    client = YouTubeClient(client_secrets)

    # Resolve username/handle to channel ID if needed
    resolved_id = client.resolve_channel_id(channel_id)
    if not resolved_id:
        console.print(f"[red]Error: Could not resolve '{channel_id}' to a channel ID[/red]")
        raise click.Abort()

    videos = client.get_channel_videos(resolved_id, max_results)

    if not videos:
        console.print("[yellow]No videos found[/yellow]")
        return

    # Display table
    table = Table(title=f"Videos from Channel {channel_id}")
    table.add_column("Video ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Published", style="green")
    table.add_column("Views", justify="right", style="yellow")

    for video in videos:
        views = str(video.statistics.view_count) if video.statistics else "N/A"
        table.add_row(
            video.id,
            video.snippet.title[:50] + "..."
            if len(video.snippet.title) > 50
            else video.snippet.title,
            video.snippet.published_at.strftime("%Y-%m-%d"),
            views,
        )

    console.print(table)
    console.print(f"\n[green]Total videos: {len(videos)}[/green]")

    # Save to file if requested
    if output:
        output_path = Path(output)
        video_data = [v.model_dump(mode="json", by_alias=True) for v in videos]
        output_path.write_text(json.dumps(video_data, indent=2))
        console.print(f"\n[green]✓[/green] Saved video list to {output}")


@cli.command()
@click.option(
    "--channel-id",
    help="YouTube channel ID, username, or @handle",
)
@click.option(
    "--video-ids",
    help="Comma-separated list of video IDs to archive",
)
@click.option(
    "--input-file",
    type=click.Path(exists=True),
    help="JSON file containing video list from 'list' command",
)
@click.option(
    "--output-dir",
    required=True,
    help="Directory to save archived videos",
)
@click.option(
    "--max-results",
    type=int,
    help="Maximum number of videos to archive",
)
@click.option(
    "--skip-existing",
    is_flag=True,
    help="Skip videos that have already been downloaded",
)
@click.option(
    "--quality",
    type=click.Choice(["best", "1080p", "720p", "480p"]),
    default="best",
    help="Video quality to download",
)
@click.option(
    "--client-secrets",
    default="client_secrets.json",
    help="Path to OAuth client secrets file",
)
def archive(
    channel_id: str | None,
    video_ids: str | None,
    input_file: str | None,
    output_dir: str,
    max_results: int | None,
    skip_existing: bool,
    quality: str,
    client_secrets: str,
):
    """Archive YouTube videos with metadata and captions."""
    client = YouTubeClient(client_secrets)
    downloader = VideoDownloader(output_dir, quality, skip_existing)

    videos = []

    # Determine source of videos
    if input_file:
        console.print(f"[cyan]Loading videos from:[/cyan] {input_file}")
        video_data = json.loads(Path(input_file).read_text())
        videos = [Video(**v) for v in video_data]
    elif channel_id:
        # Resolve username/handle to channel ID if needed
        resolved_id = client.resolve_channel_id(channel_id)
        if not resolved_id:
            console.print(f"[red]Error: Could not resolve '{channel_id}' to a channel ID[/red]")
            raise click.Abort()
        videos = client.get_channel_videos(resolved_id, max_results)
    elif video_ids:
        video_id_list = [vid.strip() for vid in video_ids.split(",")]
        for vid_id in video_id_list:
            video = client.get_video_details(vid_id)
            if video:
                videos.append(video)
    else:
        console.print("[red]Error: Must provide --channel-id, --video-ids, or --input-file[/red]")
        raise click.Abort()

    if not videos:
        console.print("[yellow]No videos to archive[/yellow]")
        return

    if max_results:
        videos = videos[:max_results]

    console.print(f"\n[bold cyan]Archiving {len(videos)} video(s) to {output_dir}[/bold cyan]\n")

    # Archive each video
    manifests = []
    for i, video in enumerate(videos, 1):
        console.print(f"[bold]Video {i}/{len(videos)}[/bold]")
        try:
            manifest = downloader.archive_video(video)
            manifests.append(manifest)
        except Exception as e:
            console.print(f"[red]✗ Error archiving {video.snippet.title}: {e}[/red]\n")
            continue

    # Save archive index
    index_path = Path(output_dir) / "archive_index.json"
    index_data = [m.model_dump(mode="json") for m in manifests]
    index_path.write_text(json.dumps(index_data, indent=2))

    console.print(
        f"\n[bold green]✓ Successfully archived {len(manifests)}/{len(videos)} videos[/bold green]"
    )
    console.print(f"[green]Archive index saved to {index_path}[/green]")


if __name__ == "__main__":
    cli()
