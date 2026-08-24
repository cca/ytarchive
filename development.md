# Development Tasks

## Setup
```bash
uv sync --extra dev

# Check for ffmpeg
command -v ffmpeg || echo "Install ffmpeg: brew install ffmpeg"
```

## Testing
```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov-report=html

# Run specific test
uv run pytest tests/test_models.py -v
```

## Linting & Formatting
```bash
# Check for issues
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

## Running the CLI
```bash
# List videos (saves to archive/videos.json)
uv run ytarchive list --channel-id UC3clbBht0DU9hCSKvoP-Z_Q

# Archive videos (reads from archive/videos.json, saves to archive/)
uv run ytarchive archive

# Or archive directly from channel
uv run ytarchive archive --channel-id UC3clbBht0DU9hCSKvoP-Z_Q
```

## Release Checklist
1. Update version in `pyproject.toml` and `src/ytarchive/__init__.py`
2. Run tests: `uv run pytest`
3. Run linting: `uv run ruff check .`
4. Run formatting: `uv run ruff format .`
5. Build: `uv build`
6. Tag release: `git tag v0.1.0`
