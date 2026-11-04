#!/usr/bin/env python3
"""
Common web scraping utility using cloudscraper and html2text.
Works in any environment without special encodings.
"""

import cloudscraper
from html2text import HTML2Text
from typing import Optional, Dict, Any


def create_scraper() -> cloudscraper.CloudScraper:
    """Create a cloudscraper instance with common settings."""
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )
    return scraper


def fetch_url(url: str, headers: Optional[Dict[str, str]] = None) -> str:
    """
    Fetch URL content using cloudscraper.
    
    Args:
        url: The URL to fetch
        headers: Optional custom headers
        
    Returns:
        HTML content as string
        
    Raises:
        Exception: If request fails
    """
    scraper = create_scraper()
    
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    response = scraper.get(url, headers=headers)
    response.raise_for_status()
    return response.text


def html_to_markdown(html_content: str, **options) -> str:
    """
    Convert HTML to clean Markdown.
    
    Args:
        html_content: HTML string to convert
        **options: Additional html2text options
        
    Returns:
        Markdown string
    """
    h = HTML2Text()
    
    # Default settings for clean output
    h.ignore_links = options.get('ignore_links', False)
    h.ignore_images = options.get('ignore_images', False)
    h.ignore_emphasis = options.get('ignore_emphasis', False)
    h.body_width = options.get('body_width', 0)  # 0 = no wrapping
    h.skip_internal_links = options.get('skip_internal_links', True)
    h.unicode_snob = options.get('unicode_snob', True)  # Use unicode instead of ASCII
    h.decode_errors = options.get('decode_errors', 'ignore')
    
    return h.handle(html_content)


def fetch_and_convert(url: str, headers: Optional[Dict[str, str]] = None, **markdown_options) -> str:
    """
    Fetch URL and convert to Markdown in one call.
    
    Args:
        url: URL to fetch
        headers: Optional custom headers
        **markdown_options: Options to pass to html_to_markdown
        
    Returns:
        Markdown string
    """
    html = fetch_url(url, headers)
    return html_to_markdown(html, **markdown_options)


def save_markdown(content: str, filepath: str) -> None:
    """
    Save markdown content to a file.
    
    Args:
        content: Markdown string to save
        filepath: Path where to save the file
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def fetch_and_save(url: str, filepath: str, headers: Optional[Dict[str, str]] = None, **markdown_options) -> None:
    """
    Fetch URL, convert to Markdown, and save to file.
    
    Args:
        url: URL to fetch
        filepath: Path where to save the markdown file
        headers: Optional custom headers
        **markdown_options: Options to pass to html_to_markdown
    """
    markdown = fetch_and_convert(url, headers, **markdown_options)
    save_markdown(markdown, filepath)


if __name__ == '__main__':
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python common_scraper.py <url> [output_file]")
        sys.exit(1)
    
    url = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        markdown = fetch_and_convert(url)
        
        if output_file:
            save_markdown(markdown, output_file)
            print(f"Saved to {output_file}")
        else:
            print(markdown)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
