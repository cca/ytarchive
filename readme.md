# ytarchive

YouTube video archival tool.

## Setup

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- YouTube Data API v3 credentials
- `uv sync`

### YouTube API Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable **YouTube Data API v3**
4. Navigate to **Credentials** → **Create Credentials** → **OAuth client ID**
5. Configure an OAuth consent screen (internal, add your own email when asked)
6. Select **Desktop app** as application type
7. Download JSON and save as `client_secrets.json` in project root
8. On first run, browser will open for OAuth consent

## Usage

### Finding a Channel

The tool accepts multiple formats:
- **Channel ID**: `UC_x5XG1OV2P6uZZ5FSM9Ttw` (starts with UC)
- **Username**: `CCAarts` (from youtube.com/user/CCAarts)
- **Handle**: `@channelname` or `channelname` (from youtube.com/@channelname)

To find manually: Visit channel → View Page Source → Search for `"channelId"` or `"externalId"`

### List all videos from a channel

```bash
# By channel ID
ytarchive list --channel-id UC_x5XG1OV2P6uZZ5FSM9Ttw

# By username
ytarchive list --channel-id CCAarts

# By handle
ytarchive list --channel-id @channelname

# Save to file for later archival
ytarchive list --channel-id CCAarts --output videos.json
```

### Archive videos

```bash
# Archive all videos from channel (by username, handle, or ID)
ytarchive archive --channel-id CCAarts --output-dir ./archive

# Archive from saved list
ytarchive archive --input-file videos.json --output-dir ./archive

# Archive specific video IDs
ytarchive archive --video-ids dQw4w9WgXcQ,jNQXAC9IVRw --output-dir ./archive
```

### Options

- `--max-results N`: Limit number of videos to process (default: all)
- `--skip-existing`: Skip videos already downloaded
- `--quality`: Video quality (best/1080p/720p/480p, default: best)

## Output Structure

```txt
archive/
├── VIDEO_ID/
│   ├── video.mp4          # Video file
│   ├── metadata.json      # Full API metadata
│   ├── captions_en.vtt    # English captions (if available)
│   ├── captions_*.vtt     # Other language captions
│   └── thumbnail.jpg      # Video thumbnail
```

## Development

```bash
# Run tests
uv run pytest
# Lint
uv run ruff check .
# Format
uv run ruff format .
```
