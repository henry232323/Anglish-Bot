#!/usr/bin/env bash
# Build the Lambda dependency layer with Linux-compatible packages so Lambda can load them.
# Run from repo root: ./infrastructure/build_layer.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LAYER_DIR="$SCRIPT_DIR/lambda_layer"
PYTHON_DIR="$LAYER_DIR/python"
REQS="$REPO_ROOT/interactions/requirements.txt"

mkdir -p "$PYTHON_DIR"
rm -rf "$PYTHON_DIR"/*
echo "Building layer for Lambda (Linux x86_64, Python 3.10)..."

if command -v docker &>/dev/null; then
  # Prefer Docker so we get exact Lambda runtime ABI (PyNaCl, cffi, etc. load correctly)
  echo "Using Docker (Lambda Python 3.10 image, linux/amd64 for x86_64 Lambda)..."
  docker run --rm --platform linux/amd64 --entrypoint "" \
    -v "$REPO_ROOT:/src:ro" \
    -v "$LAYER_DIR:/out" \
    -w /out \
    public.ecr.aws/lambda/python:3.10 \
    pip install -r /src/interactions/requirements.txt -t python/ --quiet
else
  # Fallback: pip with platform so we get manylinux wheels for Lambda (Linux)
  echo "Using local pip with --platform manylinux2014_x86_64..."
  pip install -r "$REQS" -t "$PYTHON_DIR" \
    --platform manylinux2014_x86_64 \
    --python-version 3.10 \
    --upgrade
fi

echo "Layer built at $PYTHON_DIR"
ls "$PYTHON_DIR" | head -5
echo "... (run deploy to use it)"
