#!/usr/bin/env python3
"""
Fetch release notes from GitHub and J wiki and cache them locally.
"""

import json
import requests
from bs4 import BeautifulSoup
import sys
import re

def fetch_github_release_markdown(repo, tag):
    """Fetch release notes markdown from GitHub API."""
    try:
        # Use GitHub API to get the release
        api_url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
        headers = {'Accept': 'application/vnd.github.v3+json'}
        
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Get the markdown body
        body = data.get('body', '')
        if not body:
            return "No release notes available."
        
        return body
    except Exception as e:
        return f"Error fetching release notes: {str(e)}"

def fetch_github_release(url):
    """Extract repo and tag from URL and fetch markdown."""
    try:
        # Parse GitHub URL: https://github.com/owner/repo/releases/tag/version
        match = re.match(r'https://github\.com/([^/]+)/([^/]+)/releases/tag/(.+)', url)
        if not match:
            return "Invalid GitHub URL format"
        
        owner, repo, tag = match.groups()
        return fetch_github_release_markdown(f"{owner}/{repo}", tag)
    except Exception as e:
        return f"Error: {str(e)}"

def fetch_j_wiki_release(url):
    """Fetch release notes from J wiki and convert to markdown."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the parser output div which contains the main article content
        content = soup.find('div', class_='mw-parser-output')
        if not content:
            content = soup.find('div', id='mw-content-text')
        
        if not content:
            return "Release notes not found on page."
        
        # Remove navigation elements, TOC, and other non-content
        for element in content.find_all(['div', 'table'], class_=['toc', 'navbox', 'metadata', 'ambox']):
            element.decompose()
        
        # Convert wiki HTML to markdown-like format
        markdown = []
        last_was_list = False
        
        # Get direct children to avoid nested duplication
        for element in content.children:
            if not element.name:
                continue
                
            if element.name == 'h2':
                text = element.get_text(strip=True)
                # Skip edit links
                if '[edit]' not in text and text not in ['Contents', 'Navigation menu']:
                    markdown.append(f"\n## {text}\n")
                    last_was_list = False
            elif element.name == 'h3':
                text = element.get_text(strip=True)
                if '[edit]' not in text:
                    markdown.append(f"\n### {text}\n")
                    last_was_list = False
            elif element.name == 'ul':
                # Process list items
                for li in element.find_all('li', recursive=False):
                    li_text = li.get_text(strip=True)
                    if li_text and not li_text.startswith('http'):
                        markdown.append(f"* {li_text}")
                markdown.append("")
                last_was_list = True
            elif element.name == 'p':
                text = element.get_text(strip=True)
                if text and len(text) > 10:  # Skip very short paragraphs
                    if last_was_list:
                        markdown.append("")
                    markdown.append(text)
                    markdown.append("")
                    last_was_list = False
            elif element.name == 'pre':
                code_text = element.get_text(strip=True)
                if code_text:
                    markdown.append(f"```\n{code_text}\n```")
                    markdown.append("")
                    last_was_list = False
        
        result = '\n'.join(markdown)
        # Clean up multiple blank lines
        while '\n\n\n' in result:
            result = result.replace('\n\n\n', '\n\n')
        
        return result.strip()
    except Exception as e:
        return f"Error fetching release notes: {str(e)}"

def main():
    # Load releases metadata
    with open('releases.json', 'r') as f:
        releases_data = json.load(f)
    
    # Cache for release notes
    notes_cache = {}
    
    print("Fetching release notes...")
    
    # Fetch all releases
    for lang_key, versions in releases_data['releases'].items():
        lang_data = releases_data['languages'][lang_key]
        print(f"\nFetching {lang_data['name']} releases...")
        
        for version in versions:
            # Generate URL
            url = lang_data['url_template'].replace('{version}', version)
            
            print(f"  {version}... ", end='', flush=True)
            
            # Fetch notes based on source
            if 'github.com' in url:
                notes = fetch_github_release(url)
            elif 'jsoftware.com' in url:
                notes = fetch_j_wiki_release(url)
            else:
                notes = "Unknown source"
            
            # Store in cache
            cache_key = f"{lang_key}-{version}"
            notes_cache[cache_key] = {
                "language": lang_data['name'],
                "version": version,
                "url": url,
                "notes": notes
            }
            
            print(f"✓ ({len(notes)} chars)")
    
    # Save cache
    with open('release-notes-cache.json', 'w') as f:
        json.dump(notes_cache, f, indent=2)
    
    print(f"\n✓ Cached {len(notes_cache)} releases to release-notes-cache.json")

if __name__ == '__main__':
    main()
