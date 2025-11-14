"""
Asynchronous seed crawler:
- Uses Playwright for dynamic page rendering and link extraction
- Identifies and downloads PDF files (direct + from product-like subpages)
- Stores files in ../data/raw_pdfs and metadata in ../data/meta
- Falls back to plain requests when Playwright navigation fails
"""

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

OUT_DIR = "../data/raw_pdfs"  # Target directory for downloaded PDF binaries
META_DIR = "../data/meta"     # Directory for JSON metadata per file
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(META_DIR, exist_ok=True)

SEEDS = [  # Initial seed URLs (adjust based on target domains)
    "https://www.policybazaar.com/life-insurance/term-insurance/",
    "https://www.icicilombard.com/general-insurance/health-insurance",
    "https://www.hdfcergo.com/health-insurance",
]

DEFAULT_HEADERS = {  # Mimic typical browser UA, basic language prefs
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/119.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def save_meta(meta):
    """
    Persist metadata dictionary as JSON using file hash + original name.
    Includes: url, file_name, path, hash, downloaded_at (epoch).
    """
    basename = meta["file_name"]
    jpath = os.path.join(META_DIR, basename + ".json")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

async def download_bytes(session, url, timeout=60):
    """
    Fetch raw bytes asynchronously with aiohttp for a given URL.
    Returns None on non-200 or errors.
    """
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

def requests_get_bytes(url, timeout=30):
    """
    Synchronous fallback using requests for cases where async or browser retrieval fails.
    """
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

def save_file_bytes(data, url):
    """
    Write binary PDF data to disk with a hash-prefixed filename.
    Also store JSON metadata.
    """
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

def extract_links_from_html(content, base_url):
    """
    Parse HTML content and return unique absolute links.
    Skips javascript: and fragment-only anchors.
    """
    soup = BeautifulSoup(content, "html.parser")
    found = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("javascript:") or href.startswith("#"):
            continue
        full = urljoin(base_url, href)
        found.append(full)
    return list(set(found))

async def crawl_seeds(seeds):
    """
    Orchestrate crawling:
    - Launch headless Chromium via Playwright.
    - For each seed: navigate, extract links, download direct PDFs.
    - Follow a limited number of 'deep' subpages likely to contain policy PDFs.
    - Use aiohttp for PDF download with requests fallback.
    - Fallback to plain requests if Playwright navigation fails entirely.
    """
    found_pdfs = set()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        for seed in seeds:
            print("\n-- SEED:", seed)
            try:
                context = await browser.new_context(
                    user_agent=DEFAULT_HEADERS["User-Agent"],
                    locale="en-US",
                    ignore_https_errors=True,
                    java_script_enabled=True,
                )
                page = await context.new_page()
                try:
                    await page.goto(seed, wait_until="networkidle", timeout=45000)
                except PWTimeoutError as e:
                    print("Playwright timeout for", seed, "-> trying domcontentloaded then continue")
                    try:
                        await page.goto(seed, wait_until="domcontentloaded", timeout=60000)
                    except Exception as e2:
                        print("Second attempt also failed:", e2)

                try:
                    content = await page.content()
                except Exception as e:
                    print("Could not get content from page:", e)
                    content = ""

                links = extract_links_from_html(content, seed)
                print("Found links:", len(links))

                for link in links:
                    if link.lower().endswith(".pdf") and link not in found_pdfs:
                        found_pdfs.add(link)
                        async with aiohttp.ClientSession() as sess:
                            data = await download_bytes(sess, link)
                        if not data:
                            data = requests_get_bytes(link)
                        if data:
                            meta = save_file_bytes(data, link)
                            print("Downloaded pdf:", meta["file_name"])
                        else:
                            print("Failed to download pdf:", link)

                to_follow = [l for l in links if ("policy" in l or "wording" in l or "product" in l or "brochure" in l)]
                to_follow = to_follow[:6]  # politeness limit
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