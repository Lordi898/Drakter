#!/usr/bin/env python3
"""
Scraper for shadcn/ui registry directory.
Extracts registry name, description, and links from https://ui.shadcn.com/docs/directory
"""

import json
import sys
from typing import List, Dict
from bs4 import BeautifulSoup
from common_scraper import fetch_url


def parse_registry_directory(html_content: str) -> List[Dict[str, str]]:
    """
    Parse the shadcn registry directory HTML to extract registry information.
    
    Args:
        html_content: HTML content from the directory page
        
    Returns:
        List of dictionaries with registry info (name, description, link)
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    registries = []
    
    # Registries are identified by links starting with @ symbol
    # These are the actual third-party registries in the directory
    registry_links = soup.find_all('a', string=lambda text: text and text.startswith('@'))
    
    for link in registry_links:
        name = link.get_text(strip=True)
        href = link.get('href', '')
        
        # Normalize the link to full URL if needed
        if href.startswith('/'):
            full_link = f'https://ui.shadcn.com{href}'
        else:
            full_link = href
        
        # Find the parent item container to locate the description
        item_container = link.find_parent(['div', 'article', 'li'], attrs={'data-slot': 'item'})
        if not item_container:
            item_container = link.find_parent(['div', 'article', 'li'])
        
        # Extract description from the item container
        description = ''
        if item_container:
            # Look for the description element
            desc_elem = item_container.find(['p', 'div'], attrs={'data-slot': 'item-description'})
            if desc_elem:
                description = desc_elem.get_text(strip=True)
        
        registry_info = {
            'name': name,
            'description': description,
            'link': full_link
        }
        
        registries.append(registry_info)
    
    return registries


def scrape_shadcn_directory(url: str = 'https://ui.shadcn.com/docs/directory') -> List[Dict[str, str]]:
    """
    Scrape the shadcn registry directory.
    
    Args:
        url: URL of the directory page (default: shadcn directory)
        
    Returns:
        List of dictionaries with registry information
    """
    print(f"Fetching {url}...", file=sys.stderr)
    html = fetch_url(url)
    
    print("Parsing registry information...", file=sys.stderr)
    registries = parse_registry_directory(html)
    
    print(f"Found {len(registries)} registries", file=sys.stderr)
    return registries


if __name__ == '__main__':
    try:
        # Scrape the directory
        registries = scrape_shadcn_directory()
        
        # Output as JSON for easy consumption
        print(json.dumps(registries, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
