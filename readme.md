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

**Note**: Only the `youtube.readonly` scope is needed. Captions are downloaded via yt-dlp (not the API) since the API only allows downloading captions you uploaded yourself.
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

# Run again to archive the NEXT batch (picks up where it left off)
ytarchive archive --max-results 2  # Downloads next 2 un-archived videos

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
  - For `list`: Gets first N videos from channel
  - For `archive`: Archives first N **un-archived** videos (progressive batching)
- `--overwrite`: Overwrite existing videos (default: skip existing)
- `--quality`: Video quality (best/1080p/720p/480p, default: best)
- `--output`: For list command (default: archive/videos.json)
- `--output-dir`: For archive command (default: archive)
- `--input-file`: For archive command (default: archive/videos.json)

**Progressive Archival:**
Running `archive --max-results 2` repeatedly will process 2 videos at a time, automatically skipping already-archived ones. This makes it easy to archive large channels incrementally.

## S3 Upload

Videos can be uploaded to S3 and optionally deleted locally after upload. Configure S3 via environment variables:

```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export S3_BUCKET=your-bucket
export S3_PREFIX=youtube  # optional: S3 key prefix
```

Example command:

```bash
ytarchive archive \
  --max-results 2 \
  --upload-to-s3 \
  --delete-after-upload
```

**S3 Options:**
- `--upload-to-s3`: Upload to S3 after downloading each video
- `--s3-bucket NAME`: S3 bucket (or use `S3_BUCKET` env var)
- `--s3-prefix PREFIX`: S3 key prefix (or use `S3_PREFIX` env var, default: empty)
- `--delete-after-upload`: Delete local files after successful S3 upload

Defaults to `GLACIER_IR` storage class. Videos already in S3 are automatically skipped.

## Output Structure

```txt
archive/
├── VIDEO_ID/
│   ├── video.mp4          # Video file
│   ├── metadata.json      # Full API metadata
│   ├── captions_en.vtt    # English captions (if available)
│   ├── captions_XX.vtt    # Original language captions (if different from English)
│   └── thumbnail.jpg      # Video thumbnail
```

**Note:** Only original language and English captions are downloaded to reduce noise.

## Development

```bash
# Run tests
uv run pytest

# Lint
uv run ruff check .

# Format
uv run ruff format .
```

### Quick Fixes

**"ffmpeg is not installed" error:**
```bash
brew install ffmpeg  # macOS
sudo apt-get install ffmpeg  # Linux
```

**"No supported JavaScript runtime" warning:**

**Solution:** The tool is configured to use Node.js if available, falling back to Deno.

If you have Node.js installed and still see this warning:
```bash
# Install Deno as fallback
curl -fsSL https://deno.land/install.sh | sh

# Add to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.deno/bin:$PATH"
```

**Note:** The tool uses YouTube's Android API to minimize JS runtime needs. Most videos won't require a JS runtime at all.

**Caption download errors (429 Too Many Requests):**

The tool now uses the YouTube Data API to download captions instead of yt-dlp scraping, which should avoid most rate limiting issues. Captions are downloaded using your authenticated API credentials.

## License

MIT
