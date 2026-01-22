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
    """Fetch release notes from J wiki."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the main content
        content = soup.find('div', id='content')
        if content:
            return content.get_text(separator='\n', strip=True)
        return "Release notes not found on page."
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
            version_nodots = version.replace('.', '')
            url = lang_data['url_template'].replace('{version}', version).replace('{version_nodots}', version_nodots)
            
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
