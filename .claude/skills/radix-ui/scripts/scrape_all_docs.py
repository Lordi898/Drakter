#!/usr/bin/env python3
"""
Scrape all Radix UI documentation pages and save as markdown files.

Usage: scrape_all_docs.py <section> <output_dir>
where section is one of: themes, primitives, colors
"""

import sys
import os
import re
import time
import subprocess
from pathlib import Path
from urllib.parse import urlparse

def sanitize_filename(url):
    """
    Convert URL to a safe filename.

    Example:
    https://www.radix-ui.com/themes/docs/components/button
    -> components_button.md
    """
    path = urlparse(url).path
    # Remove the base path prefix
    for prefix in ['/themes/docs/', '/primitives/docs/', '/colors/docs/']:
        if prefix in path:
            path = path.replace(prefix, '')
            break

    # Replace slashes with underscores
    filename = path.replace('/', '_')

    # Remove leading/trailing underscores
    filename = filename.strip('_')

    # Add .md extension
    if not filename.endswith('.md'):
        filename += '.md'

    return filename

def get_category_from_url(url):
    """
    Extract category from URL for organizing files.

    Example:
    https://www.radix-ui.com/themes/docs/components/button -> components
    https://www.radix-ui.com/themes/docs/overview/getting-started -> overview
    """
    path = urlparse(url).path

    # Remove base prefix
    for prefix in ['/themes/docs/', '/primitives/docs/', '/colors/docs/']:
        if prefix in path:
            path = path.replace(prefix, '')
            break

    # Get first part of the path
    parts = path.strip('/').split('/')
    if len(parts) > 0:
        return parts[0]

    return 'misc'

def scrape_url_to_file(url, output_file, scraper_script):
    """
    Scrape a URL and save to a file using the web scraper script.

    Args:
        url: URL to scrape
        output_file: Path to save the markdown content
        scraper_script: Path to scrape_url.py script
    """
    try:
        print(f"  Scraping {url}...", file=sys.stderr)

        # Run the scraper script
        result = subprocess.run(
            ['python', scraper_script, url],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            print(f"  Error scraping {url}: {result.stderr}", file=sys.stderr)
            return False

        # Save content to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.stdout)

        print(f"  Saved to {output_file}", file=sys.stderr)
        return True

    except subprocess.TimeoutExpired:
        print(f"  Timeout scraping {url}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"  Error scraping {url}: {str(e)}", file=sys.stderr)
        return False

def scrape_all_docs(section, output_dir):
    """
    Scrape all documentation for a section.

    Args:
        section: One of 'themes', 'primitives', 'colors'
        output_dir: Directory to save markdown files
    """
    # Get script paths
    script_dir = Path(__file__).parent
    discover_script = script_dir / 'discover_docs.py'
    scraper_script = script_dir / 'scrape_url.py'

    # Verify scripts exist
    if not discover_script.exists():
        raise FileNotFoundError(f"discover_docs.py not found at {discover_script}")
    if not scraper_script.exists():
        raise FileNotFoundError(f"scrape_url.py not found at {scraper_script}")

    # Discover all URLs
    print(f"Discovering {section} documentation URLs...", file=sys.stderr)
    result = subprocess.run(
        ['python', str(discover_script), section],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to discover URLs: {result.stderr}")

    urls = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]

    print(f"Found {len(urls)} pages to scrape", file=sys.stderr)

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Track statistics
    success_count = 0
    fail_count = 0

    # Scrape each URL
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}]", file=sys.stderr)

        # Get category and create subdirectory
        category = get_category_from_url(url)
        category_dir = output_path / category
        category_dir.mkdir(exist_ok=True)

        # Generate filename
        filename = sanitize_filename(url)
        output_file = category_dir / filename

        # Scrape and save
        if scrape_url_to_file(url, output_file, scraper_script):
            success_count += 1
        else:
            fail_count += 1

        # Add a small delay to be respectful
        if i < len(urls):
            time.sleep(0.5)

    # Print summary
    print("\n" + "="*50, file=sys.stderr)
    print(f"Scraping complete for {section}!", file=sys.stderr)
    print(f"Successfully scraped: {success_count}/{len(urls)} pages", file=sys.stderr)
    print(f"Failed: {fail_count}/{len(urls)} pages", file=sys.stderr)
    print(f"Output directory: {output_path}", file=sys.stderr)
    print("="*50, file=sys.stderr)

def main():
    if len(sys.argv) < 3:
        print("Usage: scrape_all_docs.py <section> <output_dir>", file=sys.stderr)
        print("\nSections:", file=sys.stderr)
        print("  themes     - Radix Themes documentation", file=sys.stderr)
        print("  primitives - Radix Primitives documentation", file=sys.stderr)
        print("  colors     - Radix Colors documentation", file=sys.stderr)
        print("\nExample:", file=sys.stderr)
        print("  scrape_all_docs.py themes ../references/themes", file=sys.stderr)
        sys.exit(1)

    section = sys.argv[1].lower()
    output_dir = sys.argv[2]

    try:
        scrape_all_docs(section, output_dir)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
