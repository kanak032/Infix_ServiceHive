#!/bin/bash

cd "$(dirname "$0")/autostream-agent"

if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment. Please ensure python3-venv is installed."
        exit 1
    fi
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Failed to install dependencies."
    exit 1
fi

if [ ! -f ".env" ]; then
    echo ""
    echo "Copying .env.example to .env..."
    cp .env.example .env
    echo ""
    echo "===================================================================="
    echo "SETUP REQUIRED:"
    echo "An .env file has been created in the autostream-agent directory."
    echo "Please open autostream-agent/.env and add your GOOGLE_API_KEY."
    echo "Once you have added the key, run this script again."
    echo "===================================================================="
    exit 0
fi

echo ""
echo "Starting AutoStream Agent..."
python agent.py
