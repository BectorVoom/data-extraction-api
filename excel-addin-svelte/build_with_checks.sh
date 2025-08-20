#!/bin/bash

# Excel Add-in Production Build Script with Validation
# This script ensures quality gates pass before deployment

set -e  # Exit immediately if any command fails

echo "🔧 Excel Add-in - Production Build with Validation Gates"
echo "========================================================"

# Ensure we're in the right directory
cd "$(dirname "$0")"

# Step 1: Install dependencies
echo "📦 Installing dependencies with Bun..."
bun install

# Step 2: Type checking and linting
echo "🔍 Running TypeScript type checking..."
bun run check

# Step 3: Build the application (BLOCKING)
echo "🏗️  Building production application..."
bun run build

# Step 4: Verify build output
echo "✅ Verifying build output..."
if [ ! -d "dist" ]; then
    echo "❌ Build failed - no dist directory found"
    exit 1
fi

if [ ! -f "dist/index.html" ]; then
    echo "❌ Build failed - no index.html found"
    exit 1
fi

# Step 5: Validate manifest.xml
echo "📋 Validating Office Add-in manifest..."
if [ ! -f "manifest.xml" ]; then
    echo "❌ No manifest.xml found"
    exit 1
fi

# Check if manifest contains required elements
if ! grep -q "taskpane" manifest.xml; then
    echo "❌ manifest.xml missing taskpane configuration"
    exit 1
fi

# Step 6: Check file sizes
echo "📊 Checking build artifact sizes..."
build_size=$(du -sh dist/ | cut -f1)
echo "   Build size: $build_size"

echo ""
echo "✅ ALL BUILD VALIDATION GATES PASSED! 🎉"
echo "🚀 Excel Add-in is ready for deployment"
echo "📋 Summary of validations:"
echo "   • Dependencies installed ✅"
echo "   • TypeScript types validated ✅"
echo "   • Production build completed ✅"
echo "   • Build artifacts verified ✅"
echo "   • Manifest.xml validated ✅"
echo "   • Build size: $build_size"
echo ""
echo "💡 Deploy the dist/ folder and manifest.xml to your Excel environment"