#!/usr/bin/env python3
"""
AniNow - Termux-friendly mirror checker, anime searcher and launcher

Features:
- Maintains a list of "mirrors" (anime sites) and checks their availability on each launch
- Marks mirrors dead and, if dead for >=48 hours, prompts to delete them on the next launch
- Lets you search for anime across mirrors and open results in your Android browser (termux-open-url or webbrowser)
- Optionally attempts playback of episode pages using yt-dlp + mpv
- Discover mirrors by scanning recent Reddit posts from configured subreddits (no API keys required)

Usage:
  - Place this file on your Termux filesystem, e.g. ~/aninow.py
  - Make executable: chmod +x aninow.py
  - Run: ./aninow.py

Requirements (recommended):
  - Python 3
  - pip install requests
  - Optional for playback: pip install yt-dlp and pkg install mpv
  - termux-open-url (Termux builtin) for opening browser links

Notes:
  - Mirrors data is stored in ~/.aninow/mirrors.json
  - The tool is interactive and conservative about adding/deleting mirrors

"""

from __future__ import annotations
import os
import sys
import json
import shutil
import subprocess
import time
import re
from datetime import datetime, timedelta
from urllib.parse import quote_plus, urlparse

try:
    import requests
except Exception:
    print("Missing dependency: requests. Install with: pip install requests")
    sys.exit(1)

__version__ = "0.1.0"

DATA_DIR = os.path.expanduser("~/.aninow")
MIRRORS_FILE = os.path.join(DATA_DIR, "mirrors.json")
TIMEOUT = 8  # seconds for mirror checks
DEAD_AGE = timedelta(hours=48)  # 48 hours

DEFAULT_MIRRORS = [
    {
        "name": "Anikoto (example)",
        "base_url": "https://anikoto.net",
        "search_template": "https://anikoto.net/?s={query}"
    },
]

URL_RE = re.compile(r"https?://[^\s'\"<>]+")


def ensure_data_dir():
    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)


def load_mirrors():
    if not os.path.isfile(MIRRORS_FILE):
        mirrors = []
        for m in DEFAULT_MIRRORS:
            mirrors.append({
                "name": m["name"],
                "base_url": m["base_url"],
                "search_template": m.get("search_template", m["base_url"]),
                "last_alive": None,
                "dead_since": None,
                "pending_delete": False
            })
        save_mirrors(mirrors)
        return mirrors
    with open(MIRRORS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_mirrors(mirrors):
    with open(MIRRORS_FILE, "w", encoding="utf-8") as f:
        json.dump(mirrors, f, indent=2, ensure_ascii=False)


def iso_now():
    return datetime.utcnow().isoformat() + "Z"


def parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", ""))
    except Exception:
        return None


def check_mirror_alive(url):
    try:
        r = requests.get(url, timeout=TIMEOUT, allow_redirects=True, headers={"User-Agent": "AniNow/1.0"})
        return r.status_code < 400
    except Exception:
        return False


def check_all_mirrors(mirrors):
    now = datetime.utcnow()
    for m in mirrors:
        base = m.get("base_url")
        alive = False
        if base:
            alive = check_mirror_alive(base)
        if alive:
            m["last_alive"] = iso_now()
            m["dead_since"] = None
            if m.get("pending_delete"):
                m["pending_delete"] = False
        else:
            if not m.get("dead_since"):
                m["dead_since"] = iso_now()
            dead_since_dt = parse_iso(m.get("dead_since"))
            if dead_since_dt and (now - dead_since_dt) >= DEAD_AGE:
                m["pending_delete"] = True
    save_mirrors(mirrors)


def report_mirrors(mirrors):
    alive = []
    dead = []
    pending = []
    for m in mirrors:
        if m.get("pending_delete"):
            pending.append(m)
        else:
            if m.get("dead_since"):
                dead.append(m)
            else:
                alive.append(m)
    print("\nMirror report:")
    print("  Alive:   {}".format(len(alive)))
    for a in alive:
        print("    - {} ({})".format(a["name"], a["base_url"]))
    print("  Dead:    {}".format(len(dead)))
    for d in dead:
        print("    - {} ({}) dead since {}".format(d["name"], d["base_url"], d.get("dead_since")))
    print("  Pending deletion (dead >=48h): {}".format(len(pending)))
    for p in pending:
        print("    - {} ({}) dead since {} [pending delete]".format(p["name"], p["base_url"], p.get("dead_since")))


def prompt_delete_pending(mirrors):
    changed = False
    pending = [m for m in list(mirrors) if m.get("pending_delete")]
    if not pending:
        return changed
    print("\nThe following mirrors have been dead for >=48 hours and are pending deletion:")
    for i, m in enumerate(pending, 1):
        print("  {}. {} ({}) - dead since {}".format(i, m["name"], m["base_url"], m.get("dead_since")))
    for m in pending:
        while True:
            ans = input("Delete mirror '{}' now? [Y/n]: ".format(m["name"])).strip().lower()
            if ans == "" or ans == "y" or ans == "yes":
                try:
                    mirrors.remove(m)
                except ValueError:
                    pass
                changed = True
                print("  Removed {}".format(m["name"]))
                break
            elif ans == "n" or ans == "no":
                m["pending_delete"] = False
                print("  Kept {}".format(m["name"]))
                break
            else:
                print("  Please answer Y (yes) or n (no).")
    if changed:
        save_mirrors(mirrors)
    return changed


def find_tools():
    tools = {
        "termux_open": shutil.which("termux-open-url") or shutil.which("termux-open"),
        "yt_dlp": shutil.which("yt-dlp") or shutil.which("yt-dlp.exe"),
        "mpv": shutil.which("mpv"),
    }
    return tools


def open_url(url, tools):
    if tools["termux_open"]:
        try:
            subprocess.run([tools["termux_open"], url])
            return True
        except Exception as e:
            print("Failed to open via termux-open: ", e)
    try:
        import webbrowser
        webbrowser.open(url)
        return True
    except Exception:
        print("No method to open URLs. Install termux-open-url or run the URL manually:")
        print(url)
        return False


def play_url_with_ytdlp(url, tools):
    if not tools["yt_dlp"]:
        print("yt-dlp not found. Install with: pip install yt-dlp")
        return
    if not tools["mpv"]:
        print("mpv not found. Install with: pkg install mpv")
        return
    try:
        proc = subprocess.run([tools["yt_dlp"], "-g", url], capture_output=True, text=True, timeout=30)
        out = proc.stdout.strip()
        if not out:
            print("yt-dlp couldn't extract a direct URL. It may require site-specific extractor or login.")
            print("Output:", proc.stderr.strip())
            return
        urls = [line.strip() for line in out.splitlines() if line.strip()]
        cmd = [tools["mpv"]] + urls
        print("Starting mpv:", " ".join(cmd))
        subprocess.run(cmd)
    except subprocess.TimeoutExpired:
        print("yt-dlp timed out trying to extract stream.")
    except Exception as e:
        print("Error running yt-dlp/mpv:", e)


def main_loop(mirrors):
    tools = find_tools()
    print("\nAniNow — mirrors checked on startup, searching and playback helper")
    print("Tools found: termux-open:{}  yt-dlp:{}  mpv:{}".format(bool(tools["termux_open"]), bool(tools["yt_dlp"]), bool(tools["mpv"])))

    q = input("\nWhat anime do you want to watch? (leave empty to manage mirrors only): ").strip()
    if not q:
        print("No search requested. Exiting.")
        return

    entries = []
    for m in mirrors:
        tpl = m.get("search_template") or m.get("base_url")
        try:
            search_url = tpl.format(query=quote_plus(q), base=m.get("base_url"))
        except Exception:
            search_url = m.get("base_url", "") + "/?s=" + quote_plus(q)
        entries.append({
            "name": m["name"],
            "url": search_url,
            "base": m.get("base_url")
        })

    print("\nSearch results (choose a mirror number to open the search page):")
    for i, e in enumerate(entries, 1):
        print("  {}. {} -> {}".format(i, e["name"], e["url"]))
    print("  0. Cancel")

    while True:
        sel = input("Open which mirror (0 to cancel)? ").strip()
        if sel == "0" or sel == "":
            print("Cancelled.")
            return
        try:
            idx = int(sel) - 1
            if 0 <= idx < len(entries):
                target = entries[idx]
                print("Opening search page on {}...".format(target["name"]))
                open_url(target["url"], tools)
                break
            else:
                print("Invalid selection.")
        except ValueError:
            print("Please enter a number.")

    while True:
        play = input("\nIf you have a direct episode URL you want to play now, paste it here (or press Enter to quit): ").strip()
        if not play:
            print("Done. Exiting AniNow.")
            break
        if play.startswith("http"):
            play_url_with_ytdlp(play, tools)
        else:
            print("Not a URL. Please paste the full https://... episode page URL.")


def add_mirror_interactive(mirrors):
    print("\nAdd a new mirror")
    name = input("  Name: ").strip()
    base = input("  Base URL (e.g. https://example.com): ").strip()
    tpl = input("  Search template (use {query} where your query should go)\n    (example: {base}/search?q={query} )\n    Leave empty to use '{base}/?s={query}': ").strip()
    if not tpl:
        tpl = base.rstrip("/") + "/?s={query}"
    newm = {
        "name": name or base,
        "base_url": base,
        "search_template": tpl,
        "last_alive": None,
        "dead_since": None,
        "pending_delete": False
    }
    mirrors.append(newm)
    save_mirrors(mirrors)
    print("Mirror added.")


def manage_mirrors_menu(mirrors):
    while True:
        print("\nMirror manager")
        for i, m in enumerate(mirrors, 1):
            status = "alive" if not m.get("dead_since") else "dead since {}".format(m.get("dead_since"))
            if m.get("pending_delete"):
                status += " (pending delete)"
            print("  {}. {} - {} - {}".format(i, m["name"], m["base_url"], status))
        print("  a. Add mirror")
        print("  q. Back")
        ch = input("Choice: ").strip().lower()
        if ch == "a":
            add_mirror_interactive(mirrors)
        elif ch == "q" or ch == "":
            save_mirrors(mirrors)
            break
        else:
            try:
                idx = int(ch) - 1
                if 0 <= idx < len(mirrors):
                    m = mirrors[idx]
                    print("Selected mirror:")
                    print(json.dumps(m, indent=2, ensure_ascii=False))
                    sub = input("Delete this mirror? [y/N]: ").strip().lower()
                    if sub == "y":
                        mirrors.pop(idx)
                        save_mirrors(mirrors)
                        print("Deleted.")
                else:
                    print("Invalid index.")
            except ValueError:
                print("Unknown command.")


# --- Reddit discovery functions ---
def extract_urls_from_text(text):
    if not text:
        return []
    return URL_RE.findall(text)


def normalize_to_base(url):
    try:
        p = urlparse(url)
        if not p.scheme or not p.hostname:
            return None
        return f"{p.scheme}://{p.hostname}"
    except Exception:
        return None


def discover_mirrors_from_reddit(mirrors, subreddits=('anime','AnimeStreaming','animedownloads'), per_sub=25):
    print("\nDiscovering candidate mirrors from Reddit (no API keys required). This may take a bit.")
    candidates = {}
    headers = {"User-Agent": "AniNow/1.0 (+https://github.com/megagayspammer-ui/AniNow)"}
    for sr in subreddits:
        try:
            url = f"https://www.reddit.com/r/{sr}/new.json?limit={per_sub}"
            r = requests.get(url, timeout=10, headers=headers)
            if r.status_code != 200:
                continue
            j = r.json()
            for child in j.get("data", {}).get("children", []):
                data = child.get("data", {})
                for u in extract_urls_from_text(data.get("url", "")):
                    base = normalize_to_base(u)
                    if base:
                        candidates[base] = candidates.get(base, 0) + 1
                for u in extract_urls_from_text(data.get("selftext", "")):
                    base = normalize_to_base(u)
                    if base:
                        candidates[base] = candidates.get(base, 0) + 1
            time.sleep(1.0)
        except Exception:
            continue

    existing_bases = {m.get("base_url").rstrip('/') for m in mirrors if m.get("base_url")}
    suggested = []
    skip_domains = ('reddit.com','imgur.com','youtube.com','youtu.be','twitter.com','github.com','drive.google.com','dropbox.com','googleusercontent.com','t.me','telegram.me','pastebin.com','mediafire.com')
    for base, count in sorted(candidates.items(), key=lambda kv: -kv[1]):
        b = base.rstrip('/')
        if b in existing_bases:
            continue
        if any(sd in b for sd in skip_domains):
            continue
        suggested.append((b, count))
    if not suggested:
        print("No obvious new candidate mirrors found on those subreddits.")
        return

    print("\nFound candidate bases (highest first):")
    for i,(b,cnt) in enumerate(suggested,1):
        print("  {}. {}  (seen {} times)".format(i, b, cnt))

    for base, cnt in suggested:
        print(f"\nCandidate: {base}  (seen {cnt} times)")
        alive = check_mirror_alive(base)
        print("  Reachable: {}".format("yes" if alive else "no"))
        ans = input("  Add as mirror? [y/N]: ").strip().lower()
        if ans == 'y':
            name = input("    Name (leave empty to use domain): ").strip() or base
            tpl = base.rstrip('/') + "/?s={query}"
            mirrors.append({
                "name": name,
                "base_url": base,
                "search_template": tpl,
                "last_alive": iso_now() if alive else None,
                "dead_since": None if alive else iso_now(),
                "pending_delete": False
            })
            save_mirrors(mirrors)
            print("  Added.")
    print("Discovery complete.")


# --- end Reddit discovery functions ---


def print_version_and_exit():
    print(f"AniNow {__version__}")
    sys.exit(0)


def run():
    ensure_data_dir()
    mirrors = load_mirrors()
    print("Checking mirrors (this may take a few seconds)...")
    check_all_mirrors(mirrors)
    report_mirrors(mirrors)
    prompt_delete_pending(mirrors)
    while True:
        print("\nMain menu: (s)earch & watch  (m)anage mirrors  (d)discover mirrors from Reddit  (q)uit  (v)ersion")
        c = input("Choice: ").strip().lower()
        if c == "s":
            main_loop(mirrors)
        elif c == "m":
            manage_mirrors_menu(mirrors)
        elif c == "d":
            discover_mirrors_from_reddit(mirrors)
        elif c == "v":
            print_version_and_exit()
        elif c == "q" or c == "":
            print("Bye.")
            break
        else:
            print("Unknown choice.")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
