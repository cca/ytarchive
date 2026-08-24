"""Video download and archival functionality."""

from datetime import datetime
from pathlib import Path

import yt_dlp
from rich.console import Console

from ytarchive.models import ArchiveManifest, Video

console = Console()


class VideoDownloader:
    """Download videos, metadata, and captions."""

    def __init__(self, output_dir: str, quality: str = "best", skip_existing: bool = False):
        self.output_dir = Path(output_dir)
        self.quality = quality
        self.skip_existing = skip_existing
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def archive_video(self, video: Video) -> ArchiveManifest:
        """Archive a single video with all metadata and captions."""
        video_dir = self.output_dir / video.id
        video_dir.mkdir(exist_ok=True)

        manifest = ArchiveManifest(
            video_id=video.id,
            title=video.snippet.title,
            archived_at=datetime.now(),
            metadata_file=str(video_dir / "metadata.json"),
        )

        # Check if already archived
        if self.skip_existing and (video_dir / "video.mp4").exists():
            console.print(f"[yellow]↷[/yellow] Skipping {video.snippet.title} (already exists)")
            return manifest

        console.print(f"\n[cyan]Archiving:[/cyan] {video.snippet.title}")

        # Save metadata
        metadata_path = video_dir / "metadata.json"
        metadata_path.write_text(video.model_dump_json(indent=2, by_alias=True))
        console.print("  [green]✓[/green] Saved metadata")

        # Download video with yt-dlp
        video_path = self._download_video(video.id, video_dir)
        if video_path:
            manifest.video_file = str(video_path)

        # Download thumbnail
        thumbnail_path = self._download_thumbnail(video.id, video_dir)
        if thumbnail_path:
            manifest.thumbnail_file = str(thumbnail_path)

        # Download captions
        caption_files = self._download_captions(video.id, video_dir)
        manifest.caption_files = caption_files

        # Save manifest
        manifest_path = video_dir / "manifest.json"
        manifest_path.write_text(manifest.model_dump_json(indent=2))

        console.print(f"[green]✓[/green] Completed archival of {video.snippet.title}\n")
        return manifest

    def _download_video(self, video_id: str, output_dir: Path) -> Path | None:
        """Download video file using yt-dlp."""
        output_template = str(output_dir / "video.%(ext)s")

        # Quality format selection
        # Use single format when possible to avoid requiring ffmpeg for merging
        format_selector = {
            "best": "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
            "1080p": "best[height<=1080][ext=mp4]/bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]",
            "720p": "best[height<=720][ext=mp4]/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]",
            "480p": "best[height<=480][ext=mp4]/bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]",
        }.get(self.quality, "best[ext=mp4]/best")

        ydl_opts = {
            "format": format_selector,
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [self._progress_hook],
            # Use Android and web clients to reduce JS runtime requirements
            "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
            # Explicitly use Node.js for JS runtime (falls back to Deno if not found)
            "js_runtimes": ["node", "deno"],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

            video_file = output_dir / "video.mp4"
            if not video_file.exists():
                # Try webm or other extensions
                possible_files = list(output_dir.glob("video.*"))
                video_file = possible_files[0] if possible_files else None

            if video_file:
                console.print("  [green]✓[/green] Downloaded video")
                return video_file
        except Exception as e:
            # Show video ID in error for clarity
            error_msg = str(e)
            console.print(f"  [red]✗[/red] Failed to download video {video_id}: {error_msg}")

        return None

    def _download_thumbnail(self, video_id: str, output_dir: Path) -> Path | None:
        """Download video thumbnail."""
        ydl_opts = {
            "skip_download": True,
            "writethumbnail": True,
            "outtmpl": str(output_dir / "thumbnail"),
            "quiet": True,
            "js_runtimes": ["node", "deno"],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

            # Find the downloaded thumbnail
            thumbnails = list(output_dir.glob("thumbnail.*"))
            if thumbnails:
                console.print("  [green]✓[/green] Downloaded thumbnail")
                return thumbnails[0]
        except Exception as e:
            console.print(f"  [yellow]⚠[/yellow] Could not download thumbnail: {e}")

        return None

    def _download_captions(self, video_id: str, output_dir: Path) -> dict[str, str]:
        """Download all available captions."""
        ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "allsubtitles": True,
            "subtitlesformat": "vtt",
            "outtmpl": str(output_dir / "captions"),
            "quiet": True,
            "ignoreerrors": True,  # Continue on errors
            "js_runtimes": ["node", "deno"],
        }

        caption_files = {}

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

            # Find downloaded caption files
            for caption_file in output_dir.glob("captions.*.vtt"):
                # Extract language code from filename (e.g., captions.en.vtt -> en)
                lang = caption_file.stem.split(".")[-1]
                caption_files[lang] = str(caption_file)

            if caption_files:
                console.print(f"  [green]✓[/green] Downloaded {len(caption_files)} caption(s)")
            else:
                console.print("  [yellow]⚠[/yellow] No captions available")
        except Exception as e:
            # Show video ID in error for clarity
            error_msg = str(e)
            console.print(
                f"  [yellow]⚠[/yellow] Could not download captions for video {video_id}: {error_msg}"
            )

        return caption_files

    def _progress_hook(self, d):
        """Progress hook for yt-dlp downloads."""
        if d["status"] == "downloading":
            # Progress is handled by yt-dlp's own output for now
            pass
