#!/usr/bin/env python3
"""
Generate CATALOGUE.md from HTML tip files.

Parses tips from both main and dev branches to create a catalogue
with production/draft states.
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


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


def extract_tip_info(content: str, file_path: str) -> Tuple[int, str]:
    """Extract tip number and title from HTML content."""
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

    return tip_number, title


def parse_tips_from_branch(branch: str) -> Dict[int, str]:
    """Parse all tips from a given branch."""
    tips = {}

    # Get all HTML files in tips/ directory
    tip_files = get_git_files(branch, "tips/")

    for file_path in tip_files:
        content = get_file_content_from_branch(branch, file_path)
        if content:
            try:
                tip_number, title = extract_tip_info(content, file_path)
                tips[tip_number] = title
            except ValueError as e:
                print(f"Warning: {e}")

    return tips


def generate_catalogue(
    main_tips: Dict[int, str],
    dev_tips: Dict[int, str],
) -> str:
    """Generate CATALOGUE.md content."""
    # Get all unique tip numbers
    all_tip_numbers = set(main_tips.keys()) | set(dev_tips.keys())

    # Create catalogue content
    content = [
        "# Galaxy Tips Catalogue",
        "",
        "| Tip # | Title | State |",
        "|-------|-------|-------|"
    ]

    for tip_num in sorted(all_tip_numbers):
        if tip_num in main_tips:
            title = main_tips[tip_num]
            state = "production"
        elif tip_num in dev_tips:
            title = dev_tips[tip_num]
            state = "draft"
        else:
            # This shouldn't happen but handle it gracefully
            title = "Unknown"
            state = "unknown"

        content.append(f"| {tip_num} | {title} | {state} |")

    return "\n".join(content) + "\n"


def main():
    """Main function to generate the catalogue."""
    # Parse tips from both branches
    print("Parsing tips from main branch...")
    main_tips = parse_tips_from_branch("origin/main")

    print("Parsing tips from dev branch...")
    dev_tips = parse_tips_from_branch("origin/dev")

    print(f"Found {len(main_tips)} tips in main, {len(dev_tips)} tips in dev")

    # Generate catalogue
    catalogue_content = generate_catalogue(main_tips, dev_tips)

    # Write to file
    with open("CATALOGUE.md", "w") as f:
        f.write(catalogue_content)

    print("CATALOGUE.md generated successfully!")


if __name__ == "__main__":
    main()
