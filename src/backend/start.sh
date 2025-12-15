#!/bin/bash

# TataSmartAgent v3.0 - Backend Startup Script
# This script sets up and starts the production backend

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║        TataSmartAgent v3.0 - Backend Startup              ║"
echo "║                                                            ║"
echo "║  🤖 Agentic AI Loan Officer                               ║"
echo "║  🧠 Powered by LangGraph + Google Gemini 2.0 Flash        ║"
echo "║  🔐 Production-Grade Underwriting                         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.10 or higher."
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
    echo ""
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found!"
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo ""
    echo "❗ IMPORTANT: Please edit .env and add your GEMINI_API_KEY"
    echo "   Get your API key from: https://aistudio.google.com/app/apikey"
    echo ""
    read -p "Press Enter after you've added your API key to .env..."
fi

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt --quiet

echo ""
echo "✅ All dependencies installed"
echo ""
echo "🚀 Starting TataSmartAgent v3.0 Backend..."
echo ""
echo "📡 Server will be available at:"
echo "   • Main API:      http://localhost:8000"
echo "   • API Docs:      http://localhost:8000/docs"
echo "   • Health Check:  http://localhost:8000/health"
echo "   • Admin Stream:  ws://localhost:8000/admin/stream"
echo ""
echo "📝 Press Ctrl+C to stop the server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start the server
python main.py

