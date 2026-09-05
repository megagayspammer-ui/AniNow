from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import requests

NAME = "GogoAnime"

# try common gogoanime domains
DOMAINS = [
    "https://gogoanime.gg",
    "https://gogoanime.ai",
    "https://gogoanime.pe",
    "https://www2.gogoanime.gg",
]


def _fetch(url):
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "AniNow/1.0"})
        if r.status_code == 200:
            return r.text
    except Exception:
        return None
    return None


def search(base, query):
    # gogoanime has search.html?keyword=
    q = query
    candidates = []
    # try provided base first then fallback domains
    bases = [base] + [d for d in DOMAINS if d != base]
    for b in bases:
        url = b.rstrip('/') + "/search.html?keyword=" + q
        html = _fetch(url)
        if not html:
            continue
        s = BeautifulSoup(html, 'html.parser')
        # results often under .last_episodes or .items
        for a in s.find_all('a', href=True):
            txt = (a.get_text() or '').strip()
            href = a['href']
            # show links often contain '/category/'
            if '/category/' in href and txt:
                full = urljoin(b, href)
                candidates.append({'title': txt, 'url': full})
        if candidates:
            break
    # dedupe
    seen = set(); out = []
    for c in candidates:
        if c['url'] in seen: continue
        seen.add(c['url']); out.append(c)
    return out


def list_episodes(show_url):
    html = _fetch(show_url)
    if not html:
        return {}
    s = BeautifulSoup(html, 'html.parser')
    ep_links = []
    # episodes are often in li a with ep
    for a in s.find_all('a', href=True):
        href = a['href']; txt = (a.get_text() or '').strip()
        if '/episode-' in href or txt.lower().startswith('ep') or 'episode' in href.lower():
            ep_links.append({'title': txt or href, 'url': urljoin(show_url, href)})
    if not ep_links:
        return {}
    # naive: return as season 1
    return {1: ep_links}
