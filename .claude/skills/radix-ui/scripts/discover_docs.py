#!/usr/bin/env python3
"""
Discover all documentation page URLs from Radix UI documentation sites.

Usage: discover_docs.py <section>
where section is one of: themes, primitives, colors
"""

import sys
import re
import cloudscraper
from bs4 import BeautifulSoup

# Base URLs for each documentation section
BASE_URLS = {
    'themes': 'https://www.radix-ui.com/themes/docs/overview/getting-started',
    'primitives': 'https://www.radix-ui.com/primitives/docs/overview/introduction',
    'colors': 'https://www.radix-ui.com/colors/docs/overview/installation'
}

# URL prefixes for filtering
URL_PREFIXES = {
    'themes': '/themes/docs/',
    'primitives': '/primitives/docs/',
    'colors': '/colors/docs/'
}

def get_headers():
    """Get default headers for requests"""
    return {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none'
    }

def discover_doc_urls(section):
    """
    Discover all documentation URLs for a given section.

    Args:
        section: One of 'themes', 'primitives', 'colors'

    Returns:
        List of full URLs for all documentation pages
    """
    if section not in BASE_URLS:
        raise ValueError(f"Invalid section: {section}. Must be one of: {', '.join(BASE_URLS.keys())}")

    base_url = BASE_URLS[section]
    url_prefix = URL_PREFIXES[section]

    # Initialize cloudscraper
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        },
        delay=1,
        allow_brotli=True
    )

    # Fetch the page
    print(f"Fetching {base_url}...", file=sys.stderr)
    response = scraper.get(base_url, headers=get_headers())

    # Parse HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all links in the page
    links = soup.find_all('a', href=True)

    # Extract unique documentation URLs
    doc_urls = set()
    for link in links:
        href = link['href']
        # Filter for documentation links
        if href.startswith(url_prefix):
            # Convert to full URL
            full_url = f"https://www.radix-ui.com{href}"
            doc_urls.add(full_url)

    # Sort URLs for consistent output
    return sorted(doc_urls)

def main():
    if len(sys.argv) < 2:
        print("Usage: discover_docs.py <section>", file=sys.stderr)
        print("\nSections:", file=sys.stderr)
        print("  themes     - Radix Themes documentation", file=sys.stderr)
        print("  primitives - Radix Primitives documentation", file=sys.stderr)
        print("  colors     - Radix Colors documentation", file=sys.stderr)
        sys.exit(1)

    section = sys.argv[1].lower()

    try:
        urls = discover_doc_urls(section)

        print(f"Found {len(urls)} documentation pages for {section}:", file=sys.stderr)
        for url in urls:
            print(url)

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
