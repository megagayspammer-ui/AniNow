from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import requests

NAME = "Anikoto"


def search(base, query):
    # base is mirror base e.g. https://anikoto.net
    url = urljoin(base, "/?s=") + query
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "AniNow/1.0"})
        if r.status_code != 200:
            return []
        s = BeautifulSoup(r.text, "html.parser")
        results = []
        # find post links
        for a in s.find_all('a', href=True):
            text = (a.get_text() or "").strip()
            href = a['href']
            if not text:
                continue
            # heuristic: link text contains query words
            if all(w.lower() in text.lower() for w in query.split()[:3]):
                results.append({'title': text, 'url': href})
        # dedupe
        seen = set()
        out = []
        for r in results:
            if r['url'] in seen:
                continue
            seen.add(r['url'])
            out.append(r)
        return out
    except Exception:
        return []


def list_episodes(show_url):
    try:
        r = requests.get(show_url, timeout=10, headers={"User-Agent": "AniNow/1.0"})
        if r.status_code != 200:
            return {}
        s = BeautifulSoup(r.text, "html.parser")
        episodes = []
        for a in s.find_all('a', href=True):
            href = a['href']
            text = (a.get_text() or "").strip()
            # heuristic for episode links: contain 'episode' or pattern like 'ep'
            if 'episode' in href.lower() or re.search(r'ep\b|episode', text.lower()):
                episodes.append({'title': text or href, 'url': href})
        # simple grouping: single season
        if not episodes:
            return {}
        return {1: episodes}
    except Exception:
        return {}
