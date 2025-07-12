#!/bin/bash


set -e 

echo "🚀 Installing dbVault Database Backup"
echo "============================================="

echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "Found Python: $python_version"

if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"; then
    echo "❌ Error: Python 3.8 or higher is required"
    echo "Please install Python 3.8+ and try again"
    exit 1
fi

if [ ! -f "setup.py" ] || [ ! -f "requirements.txt" ]; then
    echo "❌ Error: Please run this script from the dbVault directory"
    echo "Make sure setup.py and requirements.txt are present"
    exit 1
fi

echo "📋 Checking system dependencies..."

if command -v pg_dump >/dev/null 2>&1; then
    echo "✅ PostgreSQL tools found: $(pg_dump --version | head -1)"
else
    echo "⚠️  PostgreSQL tools not found"
    echo "   To backup PostgreSQL databases, install:"
    echo "   macOS: brew install postgresql"
    echo "   Ubuntu/Debian: apt-get install postgresql-client"
    echo "   RHEL/CentOS: yum install postgresql"
fi

if command -v mongodump >/dev/null 2>&1; then
    echo "✅ MongoDB tools found: $(mongodump --version | head -1)"
else
    echo "⚠️  MongoDB tools not found"
    echo "   To backup MongoDB databases, install MongoDB Database Tools:"
    echo "   https://docs.mongodb.com/database-tools/installation/"
fi

echo "📦 Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

echo "🔧 Activating virtual environment..."
source venv/bin/activate

echo "📦 Upgrading pip..."
pip install --upgrade pip

echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo "📦 Installing dbVault..."
pip install -e .

echo "🧪 Verifying installation..."
if dbvault --version >/dev/null 2>&1; then
    echo "✅ dbVault installed successfully!"
    echo ""
    echo "🎉 Installation complete!"
    echo ""
    echo "📖 Next steps:"
    echo "1. Activate the virtual environment: source venv/bin/activate"
    echo "2. Initialize configuration: dbvault init"
    echo "3. Edit the configuration file: nano config.yaml"
    echo "4. Test database connection: dbvault test --config config.yaml"
    echo "5. Create your first backup: dbvault backup --config config.yaml"
    echo ""
    echo "📚 For more information, see README.md or run: dbvault --help"
else
    echo "❌ Installation verification failed"
    echo "dbVault command not found. Check the installation output above for errors."
    exit 1
fi

echo ""
echo "💡 Tips:"
echo "• Use environment variables for sensitive data like passwords"
echo "• Set up AWS credentials if you plan to use S3 storage"
echo "• Ensure database users have appropriate backup privileges"
echo "• Test your backup and restore procedures regularly"
