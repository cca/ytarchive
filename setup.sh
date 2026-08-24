#!/usr/bin/env bash
set -e

echo "🚀 Setting up ytarchive..."
echo ""

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ ffmpeg is not installed. Install it with:"
    echo "   macOS: brew install ffmpeg"
    echo "   Linux: sudo apt-get install ffmpeg"
    exit 1
fi

echo "✓ ffmpeg found"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Install it with:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✓ uv found"

# Sync dependencies
echo "📦 Installing dependencies..."
uv sync --extra dev

echo ""
echo "✓ Dependencies installed"

# Run tests
echo ""
echo "🧪 Running tests..."
uv run pytest -v

echo ""
echo "✨ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Get YouTube API credentials from https://console.cloud.google.com/"
echo "2. Copy client_secrets.json.example to client_secrets.json"
echo "3. Fill in your credentials"
echo "4. Run: uv run ytarchive --help"
