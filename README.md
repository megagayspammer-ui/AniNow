# AniNow

AniNow is a small Termux-friendly Python tool that maintains a list of "mirrors" (anime sites), checks their availability, helps you search across mirrors, and can attempt playback using yt-dlp + mpv. It also includes a discovery mode that scans a few Reddit subreddits for candidate mirror domains.

This repository contains a single main script (aninow.py) and a sample mirrors file. It's intended to be run on Android via Termux but works on any POSIX-like environment with Python 3 and requests.

Features
- Check mirrors on every launch and report alive/dead status
- If a mirror remains dead for 48 hours it will be marked pending deletion and you will be prompted to confirm deletion on the next launch
- Search for anime across all mirrors and open the search results in your browser (termux-open-url recommended)
- Optional playback using yt-dlp + mpv (if installed)
- Discover mirrors by scanning Reddit subreddits (no API keys required)

Quick install (Termux)

1. Clone the repo

   git clone https://github.com/megagayspammer-ui/AniNow.git
   cd AniNow

2. Install dependencies

   pkg update && pkg upgrade
   pkg install python
   pip install requests
   # Optional: playback
   pip install yt-dlp
   pkg install mpv

3. Make script executable and run

   chmod +x aninow.py
   ./aninow.py

Data files
- Mirrors and state are saved under ~/.aninow/ (mirrors.json)

Security & legality
This tool only helps discover and manage URLs. Be responsible with how you use the tool and the content you access. The repository and its author are not responsible for how you use the discovered links.

Contributing
If you want site-specific scrapers or automation for particular mirrors, open an issue or create a PR. The code is intentionally simple so contributors can add site-specific modules.
