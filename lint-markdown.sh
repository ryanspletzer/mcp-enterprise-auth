#!/bin/bash
# Validate markdown files for linting issues
# Requires: npm install -g markdownlint-cli

set -e

echo "Checking for markdownlint-cli..."
if ! command -v markdownlint &> /dev/null; then
    echo "❌ markdownlint-cli not found"
    echo "   Install with: npm install -g markdownlint-cli"
    exit 1
fi

echo "✓ Found markdownlint-cli"
echo ""

echo "Running markdown linting..."
markdownlint '**/*.md' --ignore node_modules --ignore .git || {
    echo ""
    echo "❌ Markdown linting failed"
    echo "   Run 'python3 fix-markdown.py' to auto-fix code block issues"
    exit 1
}

echo ""
echo "✅ All markdown files pass linting rules"
