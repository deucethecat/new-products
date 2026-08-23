#!/usr/bin/env python3
"""
Pulls recent posts from major companies' own newsroom/blog RSS feeds,
keeps ones that look like product launches, and writes data/launches.json
for the site to read.

No API keys required — these are all public RSS feeds.
Run daily via GitHub Actions (see .github/workflows/refresh.yml).
"""
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import urllib.request

# Company name -> public RSS/Atom feed. Add or remove companies here.
FEEDS = {
    "Google":     "https://blog.google/rss/",
    "OpenAI":     "https://openai.com/news/rss.xml",
    "Meta":       "https://about.fb.com/news/feed/",
    "Microsoft":  "https://blogs.microsoft.com/feed/",
    "Samsung":    "https://news.samsung.com/global/feed",
    "Nvidia":     "https://blogs.nvidia.com/feed/",
    "Amazon":     "https://www.aboutamazon.com/news/rss",

    # Video games
    "PlayStation": "https://blog.playstation.com/feed/",
    "Xbox":        "https://news.xbox.com/en-us/feed/",

    # The lines below are good-faith guesses at newsroom feeds for
    # beauty, skincare, cars, and designer brands. I couldn't verify
    # these live (no internet access in the environment that wrote
    # this script), so check each one loads real XML in a browser
    # before relying on it — see README for how to test and swap in
    # working ones for the brands you actually care about.
    # "Sephora":       "https://www.sephora.com/rss/press.xml",
    # "L'Oréal":       "https://www.loreal.com/en/rss/",
    # "Ford":          "https://media.ford.com/content/fordmedia/fna/us/en/rss.xml",
    # "General Motors":"https://media.gm.com/media/us/en/gm/news.detail.rss.xml",
    # "LVMH":          "https://www.lvmh.com/en/rss",
}

# Only keep posts whose title/summary suggests an actual product launch,
# not funding news, earnings, policy posts, etc.
LAUNCH_KEYWORDS = re.compile(
    r"\b(launch|launches|launching|unveil|introduc|debut|announc(e|ing|es)"
    r"|now available|available today|new (phone|device|model|app|feature|product))\b",
    re.IGNORECASE,
)

MAX_AGE_DAYS = 3       # only keep posts from the last N days
MAX_PER_COMPANY = 4    # cap noisy feeds

# Ordered keyword -> category rules. First match wins, so put more
# specific categories before general ones.
CATEGORY_RULES = [
    ("Mobile Hardware", r"\b(phone|smartphone|pixel|galaxy s|iphone|foldable)\b"),
    ("Audio",            r"\b(headphones?|earbuds?|speakers?|soundbars?|audio)\b"),
    ("Wearables",        r"\b(watch|wearables?|ring|fitness tracker|band)\b"),
    ("AI / Models",      r"\b(model|llm|chatbot|chatgpt|gemini|grok|claude|agents?)\b|\bgpt\b"),
    ("Developer Tools",  r"\b(sdk|api|developer|framework|coding|ide)\b"),
    ("Beauty",           r"\b(makeup|cosmetics?|lipstick|mascara|foundation|fragrance|perfume|eau de)\b"),
    ("Skincare",         r"\b(skincare|skin care|moisturizer|serum|sunscreen|spf|cleanser|retinol|cream)\b"),
    ("Video Games",      r"\b(video game|videogame|console|playstation|xbox|nintendo|steam|dlc|expansion pack)\b"),
    ("Cars",             r"\b(car|cars|vehicle|suv|sedan|ev|electric vehicle|automaker|truck)\b"),
    ("Designer Brands",  r"\b(runway|couture|designer|fashion week|collection|handbag|capsule collection)\b"),
    ("Consumer Hardware", r"\b(device|gadget|hardware|camera|television|\btv\b|laptop|tablet|chip)\b"),
    ("Gaming",           r"\b(games?|gaming|controller)\b"),
    ("Home & Appliances", r"\b(home|appliances?|kitchen|vacuum|robot)\b"),
    ("Consumer Software", r"\b(app|apps|feature|update|software|platform|service)\b"),
]


def guess_category(title, summary):
    text = f"{title} {summary}".lower()
    for label, pattern in CATEGORY_RULES:
        if re.search(pattern, text, re.IGNORECASE):
            return label
    return "Other"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (ship-log-bot)"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


def parse_feed(xml_bytes):
    root = ET.fromstring(xml_bytes)
    items = []
    # RSS 2.0
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        pub = item.findtext("pubDate")
        items.append((title, link, desc, pub))
    # Atom fallback
    if not items:
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for entry in root.findall(".//a:entry", ns):
            title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
            link_el = entry.find("a:link", ns)
            link = link_el.get("href") if link_el is not None else ""
            desc = (entry.findtext("a:summary", default="", namespaces=ns) or "").strip()
            pub = entry.findtext("a:updated", default="", namespaces=ns)
            items.append((title, link, desc, pub))
    return items


def parse_date(raw):
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw)
    except Exception:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            return None


def clean(text, limit=180):
    text = re.sub(r"<[^>]+>", "", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return (text[:limit] + "…") if len(text) > limit else text


def main():
    now = datetime.now(timezone.utc)
    results = []

    for company, url in FEEDS.items():
        try:
            items = parse_feed(fetch(url))
        except Exception as e:
            print(f"[warn] could not fetch {company}: {e}")
            continue

        kept = 0
        for title, link, desc, pub in items:
            if kept >= MAX_PER_COMPANY:
                break
            if not LAUNCH_KEYWORDS.search(title) and not LAUNCH_KEYWORDS.search(desc):
                continue
            dt = parse_date(pub)
            if dt and (now - dt).days > MAX_AGE_DAYS:
                continue
            summary = clean(desc)
            results.append({
                "company": company,
                "title": title,
                "summary": summary,
                "url": link,
                "date": dt.strftime("%b %d") if dt else "",
                "year": dt.strftime("%Y") if dt else "",
                "timestamp": dt.isoformat() if dt else "",
                "category": guess_category(title, summary),
            })
            kept += 1

    # newest first
    results.sort(key=lambda r: r["timestamp"], reverse=True)

    out = {
        "generated_at": now.isoformat(),
        "count": len(results),
        "launches": results,
    }
    with open("data/launches.json", "w") as f:
        json.dump(out, f, indent=2)

    print(f"Wrote {len(results)} launches to data/launches.json")


if __name__ == "__main__":
    main()
