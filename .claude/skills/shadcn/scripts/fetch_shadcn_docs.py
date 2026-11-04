#!/usr/bin/env python3
"""
Automated documentation fetcher for shadcn/ui.
Fetches all docs pages and saves them as organized markdown files.
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import List, Dict
from bs4 import BeautifulSoup
from common_scraper import fetch_url, fetch_and_save


def extract_doc_links(html_content: str, base_url: str = 'https://ui.shadcn.com') -> List[Dict[str, str]]:
    """
    Extract all documentation links from the docs page.
    
    Args:
        html_content: HTML content from the docs page
        base_url: Base URL for the site
        
    Returns:
        List of dictionaries with page info (title, url, category)
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    doc_pages = []
    seen_urls = set()
    
    # Find all links in the sidebar navigation
    sidebar_links = soup.find_all('a', href=lambda x: x and x.startswith('/docs'))
    
    for link in sidebar_links:
        href = link.get('href', '')
        
        # Skip empty or duplicate links
        if not href or href in seen_urls:
            continue
            
        # Skip the directory page as we handle it separately
        if href == '/docs/directory':
            continue
        
        seen_urls.add(href)
        
        # Extract title from link text
        title = link.get_text(strip=True)
        
        # Try to determine category from URL structure
        parts = href.split('/')
        category = 'general'
        
        if len(parts) >= 3:
            if parts[2] == 'components':
                category = 'components'
            elif parts[2] == 'forms':
                category = 'forms'
            elif parts[2] == 'registry':
                category = 'registry'
            elif parts[2] in ['installation', 'cli', 'theming', 'dark-mode', 'components-json', 
                              'monorepo', 'v0', 'javascript', 'blocks', 'figma', 'mcp', 'changelog', 'legacy']:
                category = 'setup'
        
        # Build full URL
        full_url = f"{base_url}{href}"
        
        # Create a safe filename from the path
        filename = href.replace('/docs/', '').replace('/', '_') + '.md'
        
        doc_info = {
            'title': title,
            'url': full_url,
            'path': href,
            'category': category,
            'filename': filename
        }
        
        doc_pages.append(doc_info)
    
    return doc_pages


def fetch_all_docs(output_dir: str = 'shadcn_docs', delay: float = 0.5) -> None:
    """
    Fetch all shadcn documentation pages and save as markdown.
    
    Args:
        output_dir: Directory to save markdown files
        delay: Delay between requests in seconds (to be respectful)
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Create category subdirectories
    categories = ['setup', 'components', 'forms', 'registry', 'general']
    for category in categories:
        (output_path / category).mkdir(exist_ok=True)
    
    # Get list of all documentation pages
    print("Fetching documentation index...")
    index_html = fetch_url('https://ui.shadcn.com/docs')
    doc_pages = extract_doc_links(index_html)
    
    print(f"Found {len(doc_pages)} documentation pages")
    print(f"Saving to: {output_path.absolute()}\n")
    
    # Track progress
    successful = 0
    failed = []
    
    # Fetch each page
    for i, page in enumerate(doc_pages, 1):
        try:
            print(f"[{i}/{len(doc_pages)}] Fetching: {page['title']:<40} ({page['category']})")
            
            # Determine output file path
            category_dir = output_path / page['category']
            output_file = category_dir / page['filename']
            
            # Fetch and save
            fetch_and_save(
                page['url'],
                str(output_file),
                body_width=0,  # No line wrapping
                skip_internal_links=True,
                unicode_snob=True
            )
            
            successful += 1
            
            # Be respectful with delays
            if i < len(doc_pages):
                time.sleep(delay)
                
        except Exception as e:
            print(f"  ERROR: {e}")
            failed.append({'page': page, 'error': str(e)})
    
    # Summary
    print("\n" + "=" * 70)
    print(f"Successfully fetched: {successful}/{len(doc_pages)} pages")
    
    if failed:
        print(f"Failed: {len(failed)} pages")
        print("\nFailed pages:")
        for item in failed:
            print(f"  - {item['page']['title']}: {item['error']}")
    
    # Save metadata
    metadata = {
        'total_pages': len(doc_pages),
        'successful': successful,
        'failed': len(failed),
        'pages': doc_pages
    }
    
    metadata_file = output_path / 'metadata.json'
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, indent=2, fp=f, ensure_ascii=False)
    
    print(f"\nMetadata saved to: {metadata_file}")
    print(f"\nAll documentation saved to: {output_path.absolute()}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fetch all shadcn/ui documentation as markdown files'
    )
    parser.add_argument(
        '--output-dir',
        default='shadcn_docs',
        help='Output directory for markdown files (default: shadcn_docs)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=0.5,
        help='Delay between requests in seconds (default: 0.5)'
    )
    
    args = parser.parse_args()
    
    try:
        fetch_all_docs(args.output_dir, args.delay)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)
