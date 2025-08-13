#!/usr/bin/env python3
"""
Generate CATALOGUE.md from HTML tip files and GitHub issues.

Parses tips from both main and dev branches, plus GitHub issues with
"[tip request]" titles to create a catalogue with production/draft/requested states.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, NamedTuple, Any


class TipInfo(NamedTuple):
    """Information about a tip."""
    number: int
    title: str
    body: str
    state: str


def get_git_files(branch: str, path_pattern: str) -> List[str]:
    """Get list of files matching pattern from specified git branch."""
    try:
        result = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", branch],
            capture_output=True,
            text=True,
            check=True
        )
        all_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
        # Filter files that match the pattern
        return [f for f in all_files if f.startswith(path_pattern.rstrip('*'))]
    except subprocess.CalledProcessError:
        return []


def get_file_content_from_branch(branch: str, file_path: str) -> str:
    """Get content of a file from specified git branch."""
    try:
        result = subprocess.run(
            ["git", "show", f"{branch}:{file_path}"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return ""


def extract_html_body(content: str) -> str:
    """Extract and clean body content from HTML, truncated to 50 words."""
    # Remove script and style elements
    content = re.sub(
        r'<(script|style)[^>]*>.*?</\1>', '', content,
        flags=re.DOTALL | re.IGNORECASE
    )

    # Replace media elements with placeholders
    content = re.sub(r'<img[^>]*>', '<image>', content, flags=re.IGNORECASE)
    content = re.sub(
        r'<video[^>]*>.*?</video>', '<video>', content,
        flags=re.DOTALL | re.IGNORECASE
    )
    content = re.sub(
        r'<audio[^>]*>.*?</audio>', '<audio>', content,
        flags=re.DOTALL | re.IGNORECASE
    )

    # Remove all HTML tags but keep the text content
    text_content = re.sub(r'<[^>]+>', ' ', content)

    # Clean up whitespace
    text_content = re.sub(r'\s+', ' ', text_content.strip())

    # Truncate to 50 words
    words = text_content.split()
    if len(words) > 50:
        text_content = ' '.join(words[:50]) + '...'

    return text_content


def filter_media_tags(text: str) -> str:
    """Filter HTML and markdown image/media tags and replace with placeholders."""
    # Replace HTML image tags
    text = re.sub(r'<img[^>]*>', '&lt;image&gt;', text, flags=re.IGNORECASE)

    # Replace HTML video tags
    text = re.sub(
        r'<video[^>]*>.*?</video>', '&lt;video&gt;', text,
        flags=re.DOTALL | re.IGNORECASE
    )

    # Replace HTML audio tags
    text = re.sub(
        r'<audio[^>]*>.*?</audio>', '&lt;audio&gt;', text,
        flags=re.DOTALL | re.IGNORECASE
    )

    # Replace markdown images: ![alt text](url) or ![alt text](url "title")
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '&lt;image&gt;', text)

    # Remove code block markers (```language and ```)
    text = re.sub(r'```\w*\s*', '', text)
    text = re.sub(r'```', '', text)

    # Remove inline code markers
    text = re.sub(r'`([^`]+)`', r'\1', text)

    return text


def extract_tip_info(content: str, file_path: str) -> Tuple[int, str, str]:
    """Extract tip number, title, and body from HTML content."""
    # Extract tip number from filename
    filename = Path(file_path).name
    tip_match = re.match(r'(\d+)\.html', filename)
    if not tip_match:
        raise ValueError(f"Cannot extract tip number from {filename}")

    tip_number = int(tip_match.group(1))

    # Extract title from h1 tag
    h1_match = re.search(r'<h1[^>]*>\s*(.*?)\s*</h1>', content, re.DOTALL)
    if not h1_match:
        title = "No title found"
    else:
        # Clean up the title - remove extra whitespace and newlines
        title = re.sub(r'\s+', ' ', h1_match.group(1).strip())

    # Extract body content
    body = extract_html_body(content)

    # Filter media tags
    body = filter_media_tags(body)

    return tip_number, title, body


def get_github_issues() -> List[TipInfo]:
    """Fetch GitHub issues with '[tip request]' titles."""
    try:
        # Try to get repo info from git remote
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True
        )
        remote_url = result.stdout.strip()

        # Extract owner/repo from URL
        if 'github.com' in remote_url:
            # Handle both SSH and HTTPS URLs
            repo_match = re.search(
                r'github\.com[:/]([^/]+)/([^/\.]+)', remote_url
            )
            if repo_match:
                owner, repo = repo_match.groups()
            else:
                print("Warning: Could not parse GitHub repo from remote URL")
                return []
        else:
            print("Warning: Remote is not a GitHub repository")
            return []

        # Use GitHub CLI if available
        try:
            result = subprocess.run(
                ["gh", "issue", "list", "--repo", f"{owner}/{repo}",
                 "--state", "open", "--json", "number,title,body"],
                capture_output=True,
                text=True,
                check=True
            )
            issues_data = json.loads(result.stdout)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Warning: GitHub CLI not available or not authenticated")
            return []

        tip_issues = []
        for issue in issues_data:
            title = issue.get('title', '')
            if re.match(r'^\s*\[tip request\]', title, re.IGNORECASE):
                # Clean title (remove [tip request] prefix)
                clean_title = re.sub(
                    r'^\s*\[tip request\]\s*', '', title, flags=re.IGNORECASE
                ).strip()

                # Truncate body to 50 words and clean formatting
                body = issue.get('body', '') or ''
                # Replace newlines with spaces and clean up
                body = re.sub(r'\s+', ' ', body.strip())
                # Filter media tags
                body = filter_media_tags(body)
                words = body.split()
                if len(words) > 50:
                    body = ' '.join(words[:50]) + '...'

                tip_issues.append(TipInfo(
                    number=0,  # Use 0 to indicate no assigned tip number
                    title=clean_title,
                    body=body,
                    state="requested"
                ))

        return tip_issues

    except subprocess.CalledProcessError:
        print("Warning: Could not fetch GitHub issues")
        return []


def parse_tips_from_branch(branch: str, state: str) -> Dict[int, TipInfo]:
    """Parse all tips from a given branch."""
    tips = {}

    # Get all HTML files in tips/ directory
    tip_files = get_git_files(branch, "tips/")

    for file_path in tip_files:
        content = get_file_content_from_branch(branch, file_path)
        if content:
            try:
                tip_number, title, body = extract_tip_info(content, file_path)
                tips[tip_number] = TipInfo(
                    number=tip_number,
                    title=title,
                    body=body,
                    state=state
                )
            except ValueError as e:
                print(f"Warning: {e}")

    return tips


def generate_catalogue(all_tips: Dict[Any, TipInfo]) -> str:
    """Generate CATALOGUE.md content."""
    # Create catalogue content
    content = [
        "# Galaxy Tips Catalogue",
        "",
        "| Tip # | Title | Body | State |",
        "|-------|-------|------|-------|"
    ]

    # Separate numbered tips from issues
    numbered_tips = {}
    issue_tips = []

    for key, tip in all_tips.items():
        if isinstance(key, int):
            numbered_tips[key] = tip
        else:  # This is an issue
            issue_tips.append(tip)

    # Add numbered tips first (sorted by number)
    for tip_num in sorted(numbered_tips.keys()):
        tip = numbered_tips[tip_num]
        # Escape pipe characters in content for markdown table
        title = tip.title.replace('|', '\\|')
        body = tip.body.replace('|', '\\|')

        content.append(f"| {tip_num} | {title} | {body} | {tip.state} |")

    # Add issues with blank numbers
    for tip in issue_tips:
        # Escape pipe characters in content for markdown table
        title = tip.title.replace('|', '\\|')
        body = tip.body.replace('|', '\\|')

        content.append(f"|  | {title} | {body} | {tip.state} |")

    return "\n".join(content) + "\n"


def main():
    """Main function to generate the catalogue."""
    all_tips = {}

    # Parse tips from both branches
    print("Parsing tips from main branch...")
    main_tips = parse_tips_from_branch("origin/main", "production")

    print("Parsing tips from dev branch...")
    dev_tips = parse_tips_from_branch("origin/dev", "draft")

    # Fetch GitHub issues
    print("Fetching GitHub issues...")
    github_issues = get_github_issues()

    # Combine all tips, with main branch taking precedence over dev
    all_tips.update(dev_tips)  # Add dev tips first
    all_tips.update(main_tips)  # Main tips override dev tips

    # Add GitHub issues separately (they don't have assigned tip numbers)
    issue_counter = 0
    for issue in github_issues:
        # Use negative numbers to avoid conflicts with real tip numbers
        issue_key = f"issue_{issue_counter}"
        all_tips[issue_key] = issue
        issue_counter += 1

    print(f"Found {len(main_tips)} tips in main, {len(dev_tips)} tips in dev, "
          f"{len(github_issues)} GitHub issues")

    # Generate catalogue
    catalogue_content = generate_catalogue(all_tips)

    # Write to file
    with open("CATALOGUE.md", "w") as f:
        f.write(catalogue_content)

    print("CATALOGUE.md generated successfully!")


if __name__ == "__main__":
    main()
