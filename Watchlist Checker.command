#!/bin/bash
cd "$(dirname "$0")"
echo "Checking your watchlist..."
echo ""
python3 watchlist_checker.py
echo ""
echo "Done! Press any key to close."
read -n 1
