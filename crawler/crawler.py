# crawler/crawler.py
import asyncio
import json
import os
import time
import hashlib
from urllib.parse import urljoin, urlparse
import aiohttp
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError

# OUTPUT
OUT_DIR = "../data/raw_pdfs"
META_DIR = "../data/meta"
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(META_DIR, exist_ok=True)

# Seed pages - replace with your list
SEEDS = [
    "https://www.policybazaar.com/life-insurance/term-insurance/",
    "https://www.icicilombard.com/general-insurance/health-insurance",
    "https://www.hdfcergo.com/health-insurance",
]

# Headers & UA (pretend to be a normal browser)
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/119.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# small helper: save metadata
def save_meta(meta):
    basename = meta["file_name"]
    jpath = os.path.join(META_DIR, basename + ".json")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

# download using aiohttp (async)
async def download_bytes(session, url, timeout=60):
    try:
        async with session.get(url, timeout=timeout, headers=DEFAULT_HEADERS) as resp:
            if resp.status == 200:
                return await resp.read()
            else:
                print("aiohttp non-200", url, resp.status)
                return None
    except Exception as e:
        print("aiohttp error", url, e)
        return None

# synchronous fallback using requests (useful when Playwright fails)
def requests_get_bytes(url, timeout=30):
    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout, verify=True)
        if r.status_code == 200:
            return r.content
        else:
            print("requests non-200", url, r.status_code)
            return None
    except Exception as e:
        print("requests error", url, e)
        return None

# Save file helper
def save_file_bytes(data, url):
    h = hashlib.sha256(data).hexdigest()
    parsed = urlparse(url)
    name = os.path.basename(parsed.path) or "file"
    fname = f"{h}_{name}"
    path = os.path.join(OUT_DIR, fname)
    with open(path, "wb") as f:
        f.write(data)
    meta = {
        "url": url,
        "file_name": fname,
        "path": path,
        "hash": h,
        "downloaded_at": int(time.time()),
    }
    save_meta(meta)
    print("Saved", path)
    return meta

# Extract links from HTML content (beautifulsoup)
def extract_links_from_html(content, base_url):
    soup = BeautifulSoup(content, "html.parser")
    found = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("javascript:") or href.startswith("#"):
            continue
        full = urljoin(base_url, href)
        found.append(full)
    return list(set(found))

# Main crawler
async def crawl_seeds(seeds):
    found_pdfs = set()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        for seed in seeds:
            print("\n-- SEED:", seed)
            try:
                # create a fresh context per seed (isolates navigations)
                context = await browser.new_context(
                    user_agent=DEFAULT_HEADERS["User-Agent"],
                    locale="en-US",
                    ignore_https_errors=True,
                    java_script_enabled=True,
                )
                page = await context.new_page()
                # navigation with longer timeout, wait for networkidle
                try:
                    await page.goto(seed, wait_until="networkidle", timeout=45000)
                except PWTimeoutError as e:
                    print("Playwright timeout for", seed, "-> trying domcontentloaded then continue")
                    try:
                        await page.goto(seed, wait_until="domcontentloaded", timeout=60000)
                    except Exception as e2:
                        print("Second attempt also failed:", e2)

                # get page content
                try:
                    content = await page.content()
                except Exception as e:
                    print("Could not get content from page:", e)
                    content = ""

                # extract links
                links = extract_links_from_html(content, seed)
                print("Found links:", len(links))

                # first harvest direct pdf links
                for link in links:
                    if link.lower().endswith(".pdf") and link not in found_pdfs:
                        found_pdfs.add(link)
                        # try to download via aiohttp, fallback to requests
                        async with aiohttp.ClientSession() as sess:
                            data = await download_bytes(sess, link)
                        if not data:
                            data = requests_get_bytes(link)
                        if data:
                            meta = save_file_bytes(data, link)
                            print("Downloaded pdf:", meta["file_name"])
                        else:
                            print("Failed to download pdf:", link)

                # then follow product-ish pages for deeper discovery
                to_follow = [l for l in links if ("policy" in l or "wording" in l or "product" in l or "brochure" in l)]
                # limit how many subpages we follow per seed to be polite
                to_follow = to_follow[:6]
                for sub in to_follow:
                    print("Following subpage:", sub)
                    try:
                        await page.goto(sub, wait_until="networkidle", timeout=30000)
                        sub_content = await page.content()
                        sub_links = extract_links_from_html(sub_content, sub)
                        for s in sub_links:
                            if s.lower().endswith(".pdf") and s not in found_pdfs:
                                found_pdfs.add(s)
                                async with aiohttp.ClientSession() as sess:
                                    data = await download_bytes(sess, s)
                                if not data:
                                    data = requests_get_bytes(s)
                                if data:
                                    meta = save_file_bytes(data, s)
                                    print("Downloaded pdf:", meta["file_name"])
                                else:
                                    print("Failed to download pdf:", s)
                    except PWTimeoutError:
                        print("Timeout following subpage", sub)
                    except Exception as e:
                        print("Error following subpage", sub, e)
                await context.close()

            except Exception as e:
                print("fetch error", seed, e)
                # fallback: try a plain requests GET to seed and parse HTML
                try:
                    print("Attempting HTTP fallback for seed:", seed)
                    r = requests.get(seed, headers=DEFAULT_HEADERS, timeout=30, verify=True)
                    if r.status_code == 200:
                        links = extract_links_from_html(r.text, seed)
                        for link in links:
                            if link.lower().endswith(".pdf") and link not in found_pdfs:
                                found_pdfs.add(link)
                                data = requests_get_bytes(link)
                                if data:
                                    save_file_bytes(data, link)
                                else:
                                    print("fallback download failed", link)
                except Exception as e2:
                    print("Fallback failed for seed", seed, e2)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(crawl_seeds(SEEDS))
