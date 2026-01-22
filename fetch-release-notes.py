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

def element_to_markdown(element):
    """Convert a BeautifulSoup element to markdown, preserving links and formatting."""
    if not element:
        return ""
    
    # Handle text nodes
    if isinstance(element, str):
        return element
    
    result = []
    for child in element.children:
        if isinstance(child, str):
            result.append(child)
        elif child.name == 'a':
            href = child.get('href', '')
            text = child.get_text(strip=True)
            if href and text:
                result.append(f"[{text}]({href})")
            else:
                result.append(text)
        elif child.name in ['strong', 'b']:
            text = element_to_markdown(child)
            result.append(f"**{text}**")
        elif child.name in ['em', 'i']:
            text = element_to_markdown(child)
            result.append(f"*{text}*")
        elif child.name == 'code':
            text = child.get_text(strip=True)
            result.append(f"`{text}`")
        else:
            result.append(element_to_markdown(child))
    
    return ''.join(result)

def fetch_dyalog_release(url):
    """Fetch release notes from Dyalog documentation and convert to markdown."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # For docs.dyalog.com (v20.0+)
        if 'docs.dyalog.com' in url:
            # Find the main content area
            content = soup.find('article')
            if not content:
                content = soup.find('div', class_='md-content')
            
            if not content:
                return "Release notes not found on page."
            
            # Remove navigation and other non-content elements
            for element in content.find_all(['nav', 'footer']):
                element.decompose()
            
            markdown = []
            
            for element in content.children:
                if not element.name:
                    continue
                
                if element.name == 'h1':
                    text = element.get_text(strip=True)
                    markdown.append(f"# {text}\n")
                elif element.name == 'h2':
                    text = element.get_text(strip=True)
                    markdown.append(f"\n## {text}\n")
                elif element.name == 'h3':
                    text = element.get_text(strip=True)
                    markdown.append(f"\n### {text}\n")
                elif element.name == 'ul':
                    for li in element.find_all('li', recursive=False):
                        li_md = element_to_markdown(li).strip()
                        if li_md:
                            markdown.append(f"* {li_md}")
                    markdown.append("")
                elif element.name == 'p':
                    text_md = element_to_markdown(element).strip()
                    if text_md and len(text_md) > 5:
                        markdown.append(text_md)
                        markdown.append("")
                elif element.name == 'pre':
                    code_text = element.get_text(strip=True)
                    if code_text:
                        markdown.append(f"```\n{code_text}\n```")
                        markdown.append("")
        
        # For www.dyalog.com (v19.0)
        else:
            # Find main content
            content = soup.find('div', id='content')
            if not content:
                content = soup.find('main')
            
            if not content:
                return "Release notes not found on page."
            
            markdown = []
            for element in content.find_all(['h1', 'h2', 'h3', 'p', 'ul']):
                if element.name in ['h1', 'h2', 'h3']:
                    level = element.name[1]
                    text = element.get_text(strip=True)
                    if text:
                        markdown.append(f"\n{'#' * int(level)} {text}\n")
                elif element.name == 'ul':
                    for li in element.find_all('li', recursive=False):
                        li_md = element_to_markdown(li).strip()
                        if li_md:
                            markdown.append(f"* {li_md}")
                    markdown.append("")
                elif element.name == 'p':
                    text_md = element_to_markdown(element).strip()
                    if text_md and len(text_md) > 5:
                        markdown.append(text_md)
                        markdown.append("")
        
        result = '\n'.join(markdown)
        while '\n\n\n' in result:
            result = result.replace('\n\n\n', '\n\n')
        
        return result.strip()
    except Exception as e:
        return f"Error fetching release notes: {str(e)}"

def fetch_j_wiki_release(url):
    """Fetch release notes from J wiki and convert to markdown."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        response.encoding = 'utf-8'
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
                # Process list items with formatting preserved
                for li in element.find_all('li', recursive=False):
                    li_md = element_to_markdown(li).strip()
                    if li_md and not li_md.startswith('http'):
                        markdown.append(f"* {li_md}")
                markdown.append("")
                last_was_list = True
            elif element.name == 'p':
                text_md = element_to_markdown(element).strip()
                if text_md and len(text_md) > 10:  # Skip very short paragraphs
                    if last_was_list:
                        markdown.append("")
                    markdown.append(text_md)
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
            # Generate URL - handle both template-based and explicit URL mapping
            if 'releases' in lang_data:
                # Explicit URL mapping (like Dyalog)
                url = lang_data['releases'].get(version)
                if not url:
                    print(f"  {version}... ERROR: No URL found")
                    continue
            else:
                # Template-based URL (like Uiua, TinyAPL, J)
                url = lang_data['url_template'].replace('{version}', version)
            
            print(f"  {version}... ", end='', flush=True)
            
            # Fetch notes based on source
            if 'github.com' in url:
                notes = fetch_github_release(url)
            elif 'jsoftware.com' in url:
                notes = fetch_j_wiki_release(url)
            elif 'dyalog.com' in url:
                notes = fetch_dyalog_release(url)
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
