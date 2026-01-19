#!/usr/bin/env python3
"""Fix MD031 violations - ensure fenced code blocks are surrounded by blank lines."""

from pathlib import Path


def fix_md031(filepath: Path) -> tuple[int, bool]:
    """Fix code blocks not surrounded by blank lines. Returns (violations_fixed, modified)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    violations_fixed = 0
    modified = False
    in_code_block = False

    for i, line in enumerate(lines):
        # Check if line is a code fence (opening or closing)
        is_fence = line.strip().startswith('```') or line.strip().startswith('~~~~')

        if is_fence:
            if not in_code_block:
                # Opening fence
                # Check if preceded by blank line (or start of file)
                if i > 0 and new_lines and new_lines[-1].strip() != '':
                    # Previous line is not blank, add blank line
                    new_lines.append('\n')
                    violations_fixed += 1
                    modified = True
                new_lines.append(line)
                in_code_block = True
            else:
                # Closing fence
                new_lines.append(line)
                # Check if followed by blank line (or end of file)
                if i + 1 < len(lines) and lines[i + 1].strip() != '':
                    # Next line is not blank, add blank line after this fence
                    new_lines.append('\n')
                    violations_fixed += 1
                    modified = True
                in_code_block = False
        else:
            new_lines.append(line)

    # Write changes if modified
    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

    return violations_fixed, modified


def main():
    """Fix MD031 in all markdown files."""
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

        violations_fixed, modified = fix_md031(md_file)

        if modified:
            total_files_fixed += 1
            total_violations_fixed += violations_fixed
            rel_path = md_file.relative_to(repo_root)
            print(f"✓ {rel_path}: Fixed {violations_fixed} MD031 violations")

    print()
    print(f"Summary: Fixed {total_violations_fixed} MD031 violations across {total_files_fixed} files")


if __name__ == '__main__':
    main()
