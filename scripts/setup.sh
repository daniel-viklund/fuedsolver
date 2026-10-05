#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
if [[ "$(uname -s)" == "Darwin" ]]; then
  swiftc -O scripts/vision.swift -o build/vision-ocr
else
  echo 'For screenshot recognition, install Tesseract with Swedish language data (tesseract-ocr-swe).'
fi
if [[ ! -f data/swedish.txt ]]; then
  .venv/bin/python scripts/download_dictionary.py
fi
echo 'Ready. Start the website with ./scripts/run.sh'
