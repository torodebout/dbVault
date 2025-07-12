#!/bin/bash
set -e


echo "🧹 Cleaning up dbVault test containers..."

if docker ps -a --format 'table {{.Names}}' | grep -q "^dbvault-postgres-test$"; then
    echo "Removing PostgreSQL test container..."
    docker stop dbvault-postgres-test 2>/dev/null || true
    docker rm dbvault-postgres-test 2>/dev/null || true
    echo "✅ PostgreSQL container removed"
else
    echo "ℹ️ PostgreSQL container not found"
fi

if docker ps -a --format 'table {{.Names}}' | grep -q "^dbvault-mongo-test$"; then
    echo "Removing MongoDB test container..."
    docker stop dbvault-mongo-test 2>/dev/null || true
    docker rm dbvault-mongo-test 2>/dev/null || true
    echo "✅ MongoDB container removed"
else
    echo "ℹ️ MongoDB container not found"
fi

if docker ps -a --format 'table {{.Names}}' | grep -q "postgres-test"; then
    echo "Removing additional PostgreSQL containers..."
    docker stop postgres-test 2>/dev/null || true
    docker rm postgres-test 2>/dev/null || true
fi

if docker ps -a --format 'table {{.Names}}' | grep -q "mongo-test"; then
    echo "Removing additional MongoDB containers..."
    docker stop mongo-test 2>/dev/null || true
    docker rm mongo-test 2>/dev/null || true
fi

echo "🎉 Cleanup complete!"
echo ""
echo "💡 To restart test containers:"
echo "   ./scripts/setup-postgres.sh"
echo "   ./scripts/setup-mongo.sh"
