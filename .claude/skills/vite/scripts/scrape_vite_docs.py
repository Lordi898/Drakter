#!/usr/bin/env python3
"""
Custom scraper for Vite documentation from https://vite.dev/
Vite provides raw markdown versions of docs for LLM consumption.
"""

import sys
import os
import re
import time
from pathlib import Path
import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

BASE_URL = "https://vite.dev/"
DOCS_BASE = "https://vite.dev/"

def get_headers():
    """Get default headers for requests"""
    return {
        'Accept': 'text/markdown, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

def discover_urls(scraper):
    """Discover all documentation URLs from the sitemap"""
    urls = set()

    print("Discovering documentation URLs...", file=sys.stderr)

    # Get the sitemap
    try:
        sitemap_url = f"{BASE_URL}sitemap.xml"
        headers = get_headers()

        response = scraper.get(sitemap_url, headers=headers, timeout=30)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'xml')
            for loc in soup.find_all('loc'):
                url = loc.get_text()
                # Only include documentation pages
                if any(path in url for path in ['/guide/', '/config/', '/plugins/', '/assets/']):
                    urls.add(url)
            print(f"Found {len(urls)} URLs from sitemap", file=sys.stderr)
            return sorted(urls)
    except Exception as e:
        print(f"Could not fetch sitemap: {e}", file=sys.stderr)

    return []

def convert_to_raw_markdown_url(url):
    """Convert a regular vite.dev URL to its raw .md equivalent"""
    # Vite docs provide raw markdown at the same path with .md extension
    # e.g., https://vite.dev/guide/ -> https://vite.dev/guide.md
    #      https://vite.dev/config/build-options -> https://vite.dev/config/build-options.md

    parsed = urlparse(url)
    path = parsed.path.rstrip('/')

    # Add .md extension
    if not path.endswith('.md'):
        path = path + '.md'

    return f"{parsed.scheme}://{parsed.netloc}{path}"

def get_filename_from_url(url):
    """Generate a clean filename from a URL"""
    parsed = urlparse(url)
    path = parsed.path.strip('/')

    if not path:
        return 'index.md'

    # Remove leading/trailing slashes and replace with underscores
    filename = path.replace('/', '_')

    # Ensure it ends with .md
    if not filename.endswith('.md'):
        filename += '.md'

    return filename

def scrape_raw_markdown(scraper, url):
    """Scrape the raw markdown version of a Vite doc page"""
    raw_url = convert_to_raw_markdown_url(url)

    try:
        headers = get_headers()
        response = scraper.get(raw_url, headers=headers, timeout=30)

        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'text' in content_type or 'markdown' in content_type:
                return response.text
        return None
    except Exception as e:
        return None

def scrape_urls(scraper, urls, output_dir):
    """Scrape all discovered URLs and save to markdown files"""
    print(f"Fetching raw markdown for {len(urls)} pages...", file=sys.stderr)

    results = {}
    failed = []

    for i, url in enumerate(urls, 1):
        try:
            print(f"[{i}/{len(urls)}] Fetching: {url}", file=sys.stderr)

            # Try raw markdown first
            content = scrape_raw_markdown(scraper, url)

            if content is None:
                print(f"  Could not fetch raw markdown", file=sys.stderr)
                failed.append(url)
                continue

            # Clean the content
            # Remove any "Are you an LLM?" messages
            lines = content.split('\n')
            cleaned_lines = []
            skip_next = False
            for j, line in enumerate(lines):
                # Skip LLM-related messages
                if 'Are you an LLM?' in line or 'read better optimized documentation' in line:
                    continue
                # Skip the line after "Back to Hub" or similar navigation
                if skip_next:
                    skip_next = False
                    continue
                cleaned_lines.append(line)

            content = '\n'.join(cleaned_lines)

            # Generate filename
            filename = get_filename_from_url(url)
            filepath = output_dir / filename

            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                # Add URL as reference at the top
                f.write(f"<!-- Source: {url} -->\n\n")
                f.write(content)

            results[url] = filepath
            print(f"  Saved to: {filepath.name}", file=sys.stderr)

            # Be nice to the server
            time.sleep(0.3)

        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)
            failed.append(url)

    if failed:
        print(f"\nFailed to fetch {len(failed)} pages", file=sys.stderr)

    return results

def main():
    # Create references directory
    script_dir = Path(__file__).parent.parent
    refs_dir = script_dir / 'references'
    refs_dir.mkdir(exist_ok=True)

    print("Vite Documentation Scraper (Raw Markdown)", file=sys.stderr)
    print(f"Output directory: {refs_dir}", file=sys.stderr)

    # Initialize cloudscraper
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True},
        delay=1,
        allow_brotli=True
    )

    # Discover URLs
    urls = discover_urls(scraper)

    if not urls:
        print("No URLs discovered. Exiting.", file=sys.stderr)
        return 1

    print(f"\nDiscovered {len(urls)} documentation pages", file=sys.stderr)

    # Scrape all URLs
    results = scrape_urls(scraper, urls, refs_dir)

    print(f"\nComplete! Fetched {len(results)} pages to {refs_dir}", file=sys.stderr)

    return 0

if __name__ == "__main__":
    sys.exit(main())
