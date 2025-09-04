#!/bin/bash
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null
echo "Starting PDF Slurper..."
python3 start_combined.py
