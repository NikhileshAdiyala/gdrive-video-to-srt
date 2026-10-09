#!/usr/bin/env bash
# Double-clickable macOS launcher for Video to SRT generator

# Move to the script's directory
cd "$(dirname "$0")"

echo "=========================================================="
echo "🎬 Starting Video to SRT Subtitles Generator (macOS)"
echo "=========================================================="
echo ""

# 1. Check for ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  ffmpeg was not detected on your Mac."
    echo "   Audio extraction requires ffmpeg. You can install it via Homebrew:"
    echo "   brew install ffmpeg"
    echo ""
    read -p "Press [Enter] to continue anyway or Ctrl+C to abort..."
fi

# 2. Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed on this Mac."
    echo "   Please install Python 3 or Homebrew (https://brew.sh)."
    exit 1
fi

# 3. Virtual Environment setup
if [ ! -d ".venv" ]; then
    echo "📦 First-time run: Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "📦 Installing required dependencies..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    echo "✅ Setup complete!"
else
    source .venv/bin/activate
fi

# 4. Launch Streamlit Web App
echo "🚀 Launching application..."
echo "🌐 Opening http://localhost:8501 in your default browser..."
streamlit run app.py
