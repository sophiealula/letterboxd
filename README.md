# Watchlist Checker

See which films from your Letterboxd watchlist are streaming on your services.

## Setup

1. **Install Python dependencies:**
   ```bash
   pip3 install requests beautifulsoup4
   ```

2. **Open `setup.html` in your browser**, enter your Letterboxd username and select your streaming services.

3. **Copy the generated config** into `config.json`

4. **Run it:**
   ```bash
   python3 watchlist_checker.py
   ```

Or create a desktop shortcut (Mac):
```bash
echo '#!/bin/bash
cd ~/path/to/this/folder
python3 watchlist_checker.py' > ~/Desktop/"🎬 Watchlist.command"
chmod +x ~/Desktop/"🎬 Watchlist.command"
```

Then just double-click the 🎬 icon on your desktop.
