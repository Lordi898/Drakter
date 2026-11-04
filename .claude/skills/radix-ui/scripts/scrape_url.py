#!/usr/bin/env python3
"""
Web scraper using cloudscraper to bypass Cloudflare protection.
Converts HTML to clean markdown format.

Usage: scrape_url.py <url> [output_file]
"""

import sys
import io
import cloudscraper
from markdownify import markdownify as md

# Ensure stdout uses UTF-8 encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Hop-by-hop headers that should be removed
HOP_BY_HOP_HEADERS = {
    'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
    'te', 'trailers', 'transfer-encoding', 'upgrade',
}

def clean_headers(headers):
    """Remove hop-by-hop headers"""
    cleaned = {}
    for name, value in headers.items():
        if name.lower() not in HOP_BY_HOP_HEADERS:
            cleaned[name] = value
    cleaned.pop('content-encoding', None)
    cleaned.pop('content-length', None)
    return cleaned

def get_headers():
    """Get default headers for requests"""
    return {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin'
    }

def generate_origin_and_ref(url):
    """Generate origin and referrer from URL"""
    parts = url.split('/')
    protocol = parts[0]
    domain = parts[2]
    base_url = f"{protocol}//{domain}/"
    return base_url, base_url

def clean_html_to_markdown(html_content):
    """Convert HTML content to clean markdown format"""
    try:
        # Convert HTML to markdown with ATX-style headers
        markdown_content = md(html_content, heading_style="ATX")
        return markdown_content
    except Exception as e:
        print(f"Warning: Error converting HTML to markdown: {str(e)}", file=sys.stderr)
        return html_content

def scrape_url(url, clean_content=True):
    """
    Scrape a URL using cloudscraper to bypass Cloudflare protection.
    
    Args:
        url: The URL to scrape
        clean_content: Whether to convert HTML to markdown (default: True)
    
    Returns:
        String containing the page content
    """
    # Initialize cloudscraper with browser settings
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        },
        delay=1,
        allow_brotli=True
    )
    
    # Prepare headers
    headers = get_headers()
    origin, ref = generate_origin_and_ref(url)
    headers['Origin'] = origin
    headers['Referer'] = ref
    
    # Make the request
    response = scraper.get(url, headers=headers, stream=False)
    
    # Get content type
    content_type = response.headers.get('content-type', '')
    
    # Handle different content types
    if 'text' in content_type or 'html' in content_type:
        content = response.text
        # Clean HTML to markdown if requested
        if clean_content and 'html' in content_type:
            content = clean_html_to_markdown(content)
    else:
        # For binary content, try to decode as UTF-8
        try:
            content = response.content.decode('utf-8')
        except UnicodeDecodeError:
            return f"[Binary content - {len(response.content)} bytes - Content-Type: {content_type}]"
    
    return content

def main():
    if len(sys.argv) < 2:
        print("Usage: scrape_url.py <url> [output_file]", file=sys.stderr)
        print("\nExamples:", file=sys.stderr)
        print("  scrape_url.py https://example.com", file=sys.stderr)
        print("  scrape_url.py https://example.com output.md", file=sys.stderr)
        sys.exit(1)
    
    url = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        print(f"Scraping {url}...", file=sys.stderr)
        content = scrape_url(url)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Content saved to {output_file}", file=sys.stderr)
        else:
            print(content)
            
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
