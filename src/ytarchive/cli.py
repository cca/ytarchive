"""Command-line interface for ytarchive."""

import json
from datetime import UTC, datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from ytarchive.downloader import VideoDownloader
from ytarchive.models import ArchiveManifest, Video
from ytarchive.s3_uploader import S3Uploader
from ytarchive.youtube_api import YouTubeClient

console = Console()
CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option()
def cli():
    """YouTube video archival tool."""
    pass


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--channel-id",
    required=True,
    envvar="CHANNEL",
    help="YouTube channel ID, username, or @handle (or set CHANNEL)",
)
@click.option(
    "--max-results",
    type=int,
    help="Maximum number of videos to retrieve (default: all)",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default="archive/videos.json",
    help="Save video list to JSON file (default: archive/videos.json)",
)
@click.option(
    "--client-secrets",
    type=click.Path(exists=True, path_type=Path),
    default="client_secrets.json",
    help="Path to OAuth client secrets file (default: client_secrets.json)",
)
def list(channel_id: str, max_results: int | None, output: Path, client_secrets: Path):
    """List all videos from a YouTube channel."""
    client = YouTubeClient(str(client_secrets))

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

    # Save to file
    output.parent.mkdir(parents=True, exist_ok=True)
    video_data = [v.model_dump(mode="json", by_alias=True) for v in videos]
    output.write_text(json.dumps(video_data, indent=2))
    console.print(f"\n[green]✓[/green] Saved video list to {output}")


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--channel-id",
    envvar="CHANNEL",
    help="YouTube channel ID, username, or @handle (or set CHANNEL)",
)
@click.option(
    "--video-ids",
    help="Comma-separated list of video IDs to archive",
)
@click.option(
    "--input-file",
    type=click.Path(exists=True, path_type=Path),
    default="archive/videos.json",
    help="JSON file containing video list from 'list' command (default: archive/videos.json)",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default="archive",
    help="Directory to save archived videos (default: archive)",
)
@click.option(
    "--max-results",
    type=int,
    help="Maximum number of videos to archive (default: all)",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite existing videos (default: skip existing)",
)
@click.option(
    "--quality",
    type=click.Choice(["best", "1080p", "720p", "480p"]),
    default="best",
    help="Video quality to download (default: best)",
)
@click.option(
    "--client-secrets",
    type=click.Path(exists=True, path_type=Path),
    default="client_secrets.json",
    help="Path to OAuth client secrets file (default: client_secrets.json)",
)
@click.option(
    "--upload-to-s3",
    is_flag=True,
    help="Upload each archived video to S3",
)
@click.option(
    "--s3-bucket",
    envvar="S3_BUCKET",
    help="S3 bucket name (or set S3_BUCKET)",
)
@click.option(
    "--s3-prefix",
    envvar="S3_PREFIX",
    default="",
    help="S3 key prefix (or set S3_PREFIX)",
)
@click.option(
    "--delete-after-upload",
    is_flag=True,
    help="Delete local files after a successful S3 upload",
)
def archive(
    channel_id: str | None,
    video_ids: str | None,
    input_file: Path,
    output_dir: Path,
    max_results: int | None,
    overwrite: bool,
    quality: str,
    client_secrets: Path,
    upload_to_s3: bool,
    s3_bucket: str | None,
    s3_prefix: str,
    delete_after_upload: bool,
):
    """Archive YouTube videos with metadata and captions.

    Optionally upload to S3 and delete local files to save space.

    Example:

        ytarchive archive --max-results 2 --upload-to-s3 --delete-after-upload
    """
    client = YouTubeClient(str(client_secrets))
    # Invert overwrite flag: skip_existing is the opposite
    skip_existing = not overwrite
    downloader = VideoDownloader(str(output_dir), quality, skip_existing, youtube_client=client)

    # Initialize S3 uploader if requested
    s3_uploader = None
    if upload_to_s3:
        try:
            s3_uploader = S3Uploader(bucket=s3_bucket, prefix=s3_prefix)
        except Exception as e:
            console.print(f"[red]Error initializing S3 uploader: {e}[/red]")
            raise click.Abort() from e

    videos = []

    # Determine source of videos
    if channel_id:
        # Resolve username/handle to channel ID if needed
        resolved_id = client.resolve_channel_id(channel_id)
        if not resolved_id:
            console.print(f"[red]Error: Could not resolve '{channel_id}' to a channel ID[/red]")
            raise click.Abort()
        # Fetch the complete sequence so max-results can be applied after
        # already-archived videos are removed.
        videos = client.get_channel_videos(resolved_id)
    elif video_ids:
        video_id_list = [vid.strip() for vid in video_ids.split(",")]
        for vid_id in video_id_list:
            video = client.get_video_details(vid_id)
            if video:
                videos.append(video)
    elif input_file.exists():
        console.print(f"[cyan]Loading videos from:[/cyan] {input_file}")
        video_data = json.loads(input_file.read_text())
        videos = [Video(**v) for v in video_data]
    else:
        console.print(
            "[red]Error: Must provide --channel-id, --video-ids, or ensure "
            f"{input_file} exists[/red]"
        )
        raise click.Abort()

    if not videos:
        console.print("[yellow]No videos to archive[/yellow]")
        return

    # Filter out already-archived videos (unless overwrite is set)
    if not overwrite:
        original_count = len(videos)
        channel_ids = {video.snippet.channel_id for video in videos}
        uploaded_video_ids = set()
        if len(channel_ids) == 1:
            existing_index_path = output_dir / f"{next(iter(channel_ids))}.json"
            if existing_index_path.exists():
                index_data = json.loads(existing_index_path.read_text())
                uploaded_video_ids = {
                    manifest.video_id
                    for manifest in (ArchiveManifest.model_validate(item) for item in index_data)
                    if manifest.s3_uploaded
                }

        # Check both local and S3 (if S3 uploader is configured)
        videos_to_archive = []
        for v in videos:
            local_exists = (output_dir / v.id / "video.mp4").exists()
            s3_exists = v.id in uploaded_video_ids
            if not s3_exists and s3_uploader:
                s3_exists = s3_uploader.check_exists(v.id)

            if not local_exists and not s3_exists:
                videos_to_archive.append(v)

        videos = videos_to_archive
        skipped_count = original_count - len(videos)

        if skipped_count > 0:
            console.print(
                f"[cyan]Skipped {skipped_count} already-archived video(s), "
                f"{len(videos)} remaining[/cyan]"
            )

        if not videos:
            console.print(
                "[green]All videos already archived! Use --overwrite to re-download.[/green]"
            )
            return

    # Apply max-results to the filtered list
    if max_results and len(videos) > max_results:
        videos = videos[:max_results]

    mode_str = "overwrite mode" if overwrite else "skip existing mode"
    console.print(
        f"\n[bold cyan]Archiving {len(videos)} video(s) to {output_dir} ({mode_str})[/bold cyan]\n",
        highlight=False,
    )

    # Archive each video
    manifests = []
    for i, video in enumerate(videos, 1):
        console.print(f"[bold]Video {i}/{len(videos)}[/bold]")
        try:
            manifest = downloader.archive_video(video)

            # Upload to S3 if requested
            if s3_uploader:
                video_dir = output_dir / video.id
                try:
                    uploaded_files = s3_uploader.upload_directory(video_dir, video.id)

                    # Update manifest with S3 metadata
                    manifest.s3_uploaded = True
                    manifest.s3_bucket = s3_uploader.bucket
                    manifest.s3_prefix = s3_uploader.prefix
                    manifest.s3_uploaded_at = datetime.now(UTC)
                    manifest.s3_files = uploaded_files

                    # Save updated manifest
                    manifest_path = video_dir / "manifest.json"
                    manifest_path.write_text(manifest.model_dump_json(indent=2))

                    # Delete local files if requested
                    if delete_after_upload:
                        s3_uploader.cleanup_local(video_dir)

                except Exception as e:
                    console.print(f"[red]✗ S3 upload failed: {e}[/red]")
                    console.print("[yellow]⚠ Local files retained[/yellow]\n")
                    # Continue with next video despite S3 failure

            manifests.append(manifest)
        except Exception as e:
            console.print(f"[red]✗ Error archiving {video.snippet.title}: {e}[/red]\n")
            continue

    # Merge this batch into the channel's cumulative archive index.
    channel_ids = {video.snippet.channel_id for video in videos}
    if len(channel_ids) != 1:
        console.print("[red]Error: Cannot create one archive index for multiple channels[/red]")
        raise click.Abort()

    archive_channel_id = channel_ids.pop()
    index_path = output_dir / f"{archive_channel_id}.json"
    indexed_manifests = {}
    if index_path.exists():
        index_data = json.loads(index_path.read_text())
        indexed_manifests = {
            manifest.video_id: manifest
            for manifest in (ArchiveManifest.model_validate(item) for item in index_data)
        }
    indexed_manifests.update({manifest.video_id: manifest for manifest in manifests})
    index_data = [manifest.model_dump(mode="json") for manifest in indexed_manifests.values()]
    index_path.write_text(json.dumps(index_data, indent=2))

    console.print(
        f"\n[bold green]✓ Successfully archived {len(manifests)}/{len(videos)} videos[/bold green]"
    )
    console.print(f"[green]Archive index saved to {index_path}[/green]")


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--channel-id",
    envvar="CHANNEL",
    help="YouTube channel ID to check (uses JSON filename; or set CHANNEL)",
)
@click.option(
    "--input-file",
    type=click.Path(exists=True, path_type=Path),
    help="Channel archive index (default: archive/{channel-id}.json)",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default="archive",
    help="Archive directory (default: archive/)",
)
def status(channel_id: str | None, input_file: Path | None, output_dir: Path):
    """Show archival progress for a channel.

    Displays total videos, downloaded, and uploaded to S3.
    """
    output_path = Path(output_dir)

    # Determine archive index
    if input_file is None:
        if channel_id is None:
            console.print("[red]Error: Must provide either --channel-id or --input-file[/red]")
            raise click.Abort()
        input_file = output_path / f"{channel_id}.json"

    manifests = []
    if input_file.exists():
        console.print(f"[cyan]Reading:[/cyan] {input_file}")
        index_data = json.loads(input_file.read_text())
        manifests = [ArchiveManifest.model_validate(item) for item in index_data]
    else:
        console.print(f"[yellow]No archive index found at {input_file}[/yellow]")

    downloaded = len(manifests)
    uploaded_s3 = sum(manifest.s3_uploaded for manifest in manifests)
    partial = downloaded - uploaded_s3

    # Use the video catalog for the channel total when available.
    catalog_path = output_path / "videos.json"
    total = downloaded
    if catalog_path.exists():
        video_data = json.loads(catalog_path.read_text())
        videos = [Video(**item) for item in video_data]
        if channel_id:
            videos = [video for video in videos if video.snippet.channel_id == channel_id]
        total = max(len(videos), downloaded)

    # Calculate percentages
    downloaded_pct = (downloaded / total * 100) if total > 0 else 0
    uploaded_pct = (uploaded_s3 / total * 100) if total > 0 else 0

    # Display results
    console.print("\n[bold]Archive Status:[/bold]")
    console.print(f"  Total videos:     {total}")
    console.print(f"  Downloaded:       {downloaded} ({downloaded_pct:.1f}%)")
    console.print(f"  Uploaded to S3:   {uploaded_s3} ({uploaded_pct:.1f}%)")
    if partial > 0:
        console.print(f"  [yellow]Local only:[/yellow]      {partial} (not uploaded)")
    remaining = total - downloaded
    if remaining > 0:
        console.print(f"  [cyan]Remaining:[/cyan]        {remaining}")
    else:
        console.print("\n[bold green]✓ All videos archived![/bold green]")


if __name__ == "__main__":
    cli()
