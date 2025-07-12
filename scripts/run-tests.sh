#!/bin/bash
set -e


echo "🧪 Running dbVault Test Suite"
echo "=============================="

if ! command -v pytest >/dev/null 2>&1; then
    echo "❌ pytest not found. Installing pytest..."
    pip install pytest pytest-mock
fi

echo "📦 Checking test dependencies..."
pip install -q pytest pytest-mock click pyyaml

echo ""
echo "🚀 Running tests..."
echo ""

pytest tests/ -v --tb=short

echo ""
echo "📊 Test Summary:"
echo "   Location: tests/"
echo "   Framework: pytest"
echo "   Coverage: CLI commands, database handlers, storage handlers"
echo ""
echo "💡 To run specific tests:"
echo "   pytest tests/test_cli.py -v          # CLI tests only"
echo "   pytest tests/test_database.py -v     # Database tests only"
echo "   pytest tests/test_storage.py -v      # Storage tests only"
