#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "🚀 Starting Deployment Script..."

# 1. Update pip
pip install --upgrade pip

# 2. Install dependencies from requirements.txt
if [ -f requirements.txt ]; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
else
    echo "⚠️ requirements.txt not found!"
fi

echo "🤖 Starting the Telegram Bot..."

# 3. Run the bot
# We use 'python' because Render's virtual environment maps it automatically
python bot.py