#!/bin/bash
set -e


echo "🏗️ Setting up dbVault Development Environment"
echo "=============================================="

if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "✅ Docker is running"

echo ""
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "🛠️ Installing development dependencies..."
pip install pytest pytest-mock black flake8 mypy

echo ""
echo "🗄️ Setting up test databases..."
./scripts/setup-postgres.sh
echo ""
./scripts/setup-mongo.sh

echo ""
echo "🧪 Running quick verification tests..."

echo "Testing PostgreSQL connection..."
python -m src.main test --config config/postgres.yaml --type database

echo "Testing MongoDB connection..."
python -m src.main test --config config/mongo-s3-test.yaml --type database

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "📋 What's been set up:"
echo "   ✅ Python dependencies installed"
echo "   ✅ Development tools installed (pytest, black, flake8, mypy)"
echo "   ✅ PostgreSQL test container with sample data"
echo "   ✅ MongoDB test container with sample data"
echo "   ✅ Database connections verified"
echo ""
echo "🚀 Quick Start Commands:"
echo "   ./scripts/run-tests.sh                    "
echo "   python -m src.main backup --config config/postgres.yaml --storage local"
echo "   python -m src.main list-backups --storage local"
echo "   python -m src.main test --config config/postgres.yaml"
echo ""
echo "🧹 Cleanup:"
echo "   ./scripts/cleanup.sh                      "
