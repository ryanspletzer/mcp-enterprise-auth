#!/usr/bin/env python3
"""Fix MD032 violations - ensure lists are surrounded by blank lines."""

import re
from pathlib import Path


def is_list_item(line: str) -> bool:
    """Check if a line is a list item (unordered or ordered)."""
    stripped = line.lstrip()
    # Unordered list: starts with -, *, or +
    if re.match(r'^[-*+]\s', stripped):
        return True
    # Ordered list: starts with number followed by . or )
    if re.match(r'^\d+[.)]\s', stripped):
        return True
    return False


def is_blank(line: str) -> bool:
    """Check if a line is blank or whitespace-only."""
    return line.strip() == ''


def is_code_fence(line: str) -> bool:
    """Check if a line is a code fence."""
    return line.strip().startswith('```') or line.strip().startswith('~~~~')


def fix_md032(filepath: Path) -> tuple[int, bool]:
    """Fix MD032 violations in a file. Returns (violations_fixed, modified)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    violations_fixed = 0
    modified = False
    in_code_block = False

    for i, line in enumerate(lines):
        # Track code blocks
        if is_code_fence(line):
            in_code_block = not in_code_block
            new_lines.append(line)
            continue

        # Skip processing inside code blocks
        if in_code_block:
            new_lines.append(line)
            continue

        # Check if this is a list item
        if is_list_item(line):
            # Check if previous line should have been blank
            if i > 0 and not is_blank(lines[i-1]) and not is_list_item(lines[i-1]):
                # Previous line is not blank and not a list item
                # Insert blank line before this list
                new_lines.append('\n')
                violations_fixed += 1
                modified = True
            new_lines.append(line)
        else:
            # Not a list item
            # Check if previous line was a list item (end of list)
            if i > 0 and is_list_item(lines[i-1]) and not is_blank(line):
                # Previous was list, current is not blank
                # Insert blank line after the list
                new_lines.append('\n')
                violations_fixed += 1
                modified = True
            new_lines.append(line)

    # Write changes if modified
    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

    return violations_fixed, modified


def main():
    """Fix MD032 in all markdown files."""
    repo_root = Path(__file__).parent

    # Find all markdown files
    md_files = list(repo_root.glob('**/*.md'))

    print(f"Found {len(md_files)} markdown files")
    print()

    total_files_fixed = 0
    total_violations_fixed = 0

    for md_file in sorted(md_files):
        # Skip node_modules and other common directories
        if any(part in md_file.parts for part in ['.git', 'node_modules', '.venv', 'venv']):
            continue

        violations_fixed, modified = fix_md032(md_file)

        if modified:
            total_files_fixed += 1
            total_violations_fixed += violations_fixed
            rel_path = md_file.relative_to(repo_root)
            print(f"✓ {rel_path}: Fixed {violations_fixed} MD032 violations")

    print()
    print(f"Summary: Fixed {total_violations_fixed} MD032 violations across {total_files_fixed} files")


if __name__ == '__main__':
    main()
