"""YouTube API client."""

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from rich.console import Console

from ytarchive.models import Caption, Video

SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
TOKEN_FILE = Path.home() / ".ytarchive_token.json"

console = Console()


class YouTubeClient:
    """YouTube Data API v3 client."""

    def __init__(self, client_secrets_file: str = "client_secrets.json"):
        self.client_secrets_file = client_secrets_file
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with YouTube API using OAuth2."""
        creds = None

        if TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, SCOPES)
                creds = flow.run_local_server(port=0)

            TOKEN_FILE.write_text(creds.to_json())

        self.service = build("youtube", "v3", credentials=creds)
        console.print("[green]✓[/green] Authenticated with YouTube API")

    def resolve_channel_id(self, identifier: str) -> str | None:
        """Resolve username, handle, or custom URL to channel ID.

        Args:
            identifier: Can be a channel ID (UC...), username, or @handle

        Returns:
            Channel ID if found, None otherwise
        """
        # If it already looks like a channel ID, return it
        if identifier.startswith("UC"):
            return identifier

        # Remove @ prefix if present (for handles)
        if identifier.startswith("@"):
            identifier = identifier[1:]

        # Try to find by username
        console.print(f"[cyan]Resolving channel identifier:[/cyan] {identifier}")

        try:
            # Try forUsername parameter (legacy usernames)
            response = self.service.channels().list(part="id", forUsername=identifier).execute()

            if response.get("items"):
                channel_id = response["items"][0]["id"]
                console.print(f"[green]✓[/green] Resolved to channel ID: {channel_id}")
                return channel_id

            # Try searching by handle (newer format)
            search_response = (
                self.service.search()
                .list(part="id", q=identifier, type="channel", maxResults=5)
                .execute()
            )

            if search_response.get("items"):
                # Return first match
                channel_id = search_response["items"][0]["id"]["channelId"]
                console.print(f"[green]✓[/green] Found channel ID: {channel_id}")
                return channel_id

        except Exception as e:
            console.print(f"[red]Error resolving channel:[/red] {e}")

        return None

    def get_channel_videos(self, channel_id: str, max_results: int | None = None) -> list[Video]:
        """Get all videos from a channel."""
        videos = []
        next_page_token = None

        console.print(f"[cyan]Fetching videos from channel:[/cyan] {channel_id}")

        while True:
            # Get uploads playlist ID
            channel_response = (
                self.service.channels()
                .list(part="contentDetails", id=channel_id, maxResults=1)
                .execute()
            )

            if not channel_response.get("items"):
                console.print("[red]Channel not found[/red]")
                break

            uploads_playlist_id = channel_response["items"][0]["contentDetails"][
                "relatedPlaylists"
            ]["uploads"]

            # Get videos from uploads playlist
            playlist_response = (
                self.service.playlistItems()
                .list(
                    part="snippet",
                    playlistId=uploads_playlist_id,
                    maxResults=min(50, max_results) if max_results else 50,
                    pageToken=next_page_token,
                )
                .execute()
            )

            video_ids = [
                item["snippet"]["resourceId"]["videoId"] for item in playlist_response["items"]
            ]

            # Get full video details
            videos_response = (
                self.service.videos()
                .list(part="snippet,statistics,contentDetails", id=",".join(video_ids))
                .execute()
            )

            batch_videos = [Video(**item) for item in videos_response.get("items", [])]
            videos.extend(batch_videos)

            console.print(f"  Fetched {len(videos)} videos...")

            next_page_token = playlist_response.get("nextPageToken")

            if not next_page_token or (max_results and len(videos) >= max_results):
                break

        if max_results:
            videos = videos[:max_results]

        console.print(f"[green]✓[/green] Retrieved {len(videos)} videos")
        return videos

    def get_video_details(self, video_id: str) -> Video | None:
        """Get details for a specific video."""
        response = (
            self.service.videos()
            .list(part="snippet,statistics,contentDetails", id=video_id)
            .execute()
        )

        items = response.get("items", [])
        return Video(**items[0]) if items else None

    def get_captions(self, video_id: str) -> list[Caption]:
        """Get available caption tracks for a video."""
        try:
            response = self.service.captions().list(part="snippet", videoId=video_id).execute()

            return [
                Caption(
                    id=item["id"],
                    language=item["snippet"]["language"],
                    name=item["snippet"]["name"],
                    isAutoGenerated=item["snippet"].get("isAutoGenerated", False),
                )
                for item in response.get("items", [])
            ]
        except Exception as e:
            console.print(f"[yellow]Warning: Could not fetch captions for {video_id}: {e}[/yellow]")
            return []
