# ytarchive

YouTube video archival tool.

## Setup

### Prerequisites

- Python 3.11+
- **ffmpeg** (required): `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux)
- [uv](https://github.com/astral-sh/uv) package manager
- YouTube Data API v3 credentials

### Installation

```bash
# Install ffmpeg first
brew install ffmpeg  # macOS
# OR
sudo apt-get install ffmpeg  # Linux

# Install Python dependencies
uv sync
```

**Optional**: Use [mise](https://mise.jdx.dev/) for automatic environment setup:
```bash
mise install
mise run setup
```

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

### Quick Start Workflow

```bash
# 1. List all videos from CCA channel (saves to archive/videos.json)
uv run ytarchive list --channel-id UC3clbBht0DU9hCSKvoP-Z_Q
# 2. Download videos ten at a time (reads archive/videos.json, saves to archive/)
uv run ytarchive archive --max-results 10
```

### Finding a Channel

The tool accepts multiple formats:
- **Channel ID**: `UC3clbBht0DU9hCSKvoP-Z_Q` (starts with UC)
- **Username**: `CCAarts` (from youtube.com/user/CCAarts)
- **Handle**: `@channelname` or `channelname` (from youtube.com/@channelname)

To find manually: Visit channel → View Page Source → Search for `"channelId"` or `"externalId"`

### List all videos from a channel

```bash
# By channel ID (saves to archive/videos.json by default)
ytarchive list --channel-id UC3clbBht0DU9hCSKvoP-Z_Q
# By username
ytarchive list --channel-id CCAarts
# By handle
ytarchive list --channel-id @channelname
# Custom output location
ytarchive list --channel-id CCAarts --output my-videos.json
```

### Archive videos

```bash
# Archive from default list location (archive/videos.json, skips existing by default)
ytarchive archive
# Archive from channel directly
ytarchive archive --channel-id UC3clbBht0DU9hCSKvoP-Z_Q
# Archive and overwrite existing files
ytarchive archive --overwrite
# Archive specific video IDs
ytarchive archive --video-ids dQw4w9WgXcQ,jNQXAC9IVRw
# Custom output directory
ytarchive archive --output-dir ./my-archive
```

### Options

- `--max-results N`: Limit number of videos to process (default: all)
- `--overwrite`: Overwrite existing videos (default: skip existing)
- `--quality`: Video quality (best/1080p/720p/480p, default: best)
- `--output`: For list command (default: archive/videos.json)
- `--output-dir`: For archive command (default: archive)
- `--input-file`: For archive command (default: archive/videos.json)

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

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed solutions to common issues.

### Quick Fixes

**"ffmpeg is not installed" error:**
```bash
brew install ffmpeg  # macOS
sudo apt-get install ffmpeg  # Linux
```

**"No supported JavaScript runtime" warning:**

The tool uses YouTube's Android API to minimize JS requirements. If you still see this warning:
- Install Deno: `curl -fsSL https://deno.land/install.sh | sh`
- Or use mise: `mise install` (provides Node.js 20 automatically)

**More help:** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for comprehensive solutions.

## License

MIT
