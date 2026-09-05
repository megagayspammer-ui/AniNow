from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import requests

NAME = "Generic"


def search(base, query):
    # generic search using ?s= or /search?q=
    q = query
    urls = [base.rstrip('/') + '/?s=' + q, base.rstrip('/') + '/search?q=' + q]
    results = []
    for url in urls:
        try:
            r = requests.get(url, timeout=8, headers={"User-Agent": "AniNow/1.0"})
            if r.status_code != 200:
                continue
            s = BeautifulSoup(r.text, 'html.parser')
            for a in s.find_all('a', href=True):
                txt = (a.get_text() or '').strip(); href = a['href']
                if not txt:
                    continue
                if q.lower() in txt.lower():
                    results.append({'title': txt, 'url': urljoin(base, href)})
        except Exception:
            continue
    # dedupe
    seen = set(); out = []
    for r in results:
        if r['url'] in seen: continue
        seen.add(r['url']); out.append(r)
    return out


def list_episodes(show_url):
    try:
        r = requests.get(show_url, timeout=8, headers={"User-Agent": "AniNow/1.0"})
        if r.status_code != 200:
            return {}
        s = BeautifulSoup(r.text, 'html.parser')
        episodes = []
        for a in s.find_all('a', href=True):
            href = a['href']; txt = (a.get_text() or '').strip()
            if not txt:
                continue
            if 'episode' in href.lower() or txt.lower().startswith('ep') or 'episode' in txt.lower():
                episodes.append({'title': txt, 'url': urljoin(show_url, href)})
        if not episodes:
            return {}
        return {1: episodes}
    except Exception:
        return {}
