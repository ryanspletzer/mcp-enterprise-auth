#!/usr/bin/env python3
"""Fix markdown linting issues - add language specifiers to code blocks."""

import os
import re
from pathlib import Path


def detect_language(block_content: str) -> str:
    """Detect the appropriate language for a code block based on its content."""
    content = block_content.strip()

    # Check for specific patterns
    if not content:
        return "text"

    # Shell/Bash commands
    if any(content.startswith(cmd) for cmd in ['$', '#', 'cd ', 'ls ', 'mkdir ', 'cp ', 'mv ', 'rm ',
                                                  'git ', 'docker ', 'npm ', 'pip ', 'python ',
                                                  'curl ', 'wget ', 'export ', 'echo ', 'cat ',
                                                  'uvicorn', 'pytest', 'uv ']):
        return "bash"

    # Python
    if any(kw in content for kw in ['def ', 'class ', 'import ', 'from ', 'print(',
                                      'if __name__', 'async def', 'await ']):
        return "python"

    # JSON
    if (content.startswith('{') or content.startswith('[')) and ('"' in content or "'" in content):
        if ':' in content:
            return "json"

    # YAML
    if re.search(r'^\w+:\s*\n', content, re.MULTILINE) or re.search(r'^  \w+:', content, re.MULTILINE):
        return "yaml"

    # Environment files
    if re.search(r'^[A-Z_]+=', content, re.MULTILINE):
        return "bash"

    # HTTP requests/responses
    if any(method in content for method in ['GET /', 'POST /', 'PUT /', 'DELETE /', 'HTTP/', 'Content-Type:']):
        return "http"

    # Directory trees and ASCII art
    if any(char in content for char in ['│', '├', '└', '─', '┌', '┐', '┘', '┴', '┬']):
        return "text"

    # Multi-line with indentation (likely directory structure or logs)
    lines = content.split('\n')
    if len(lines) > 5 and sum(1 for line in lines if line.startswith('  ') or line.startswith('    ')) > len(lines) * 0.3:
        return "text"

    # TypeScript/JavaScript
    if any(kw in content for kw in ['function ', 'const ', 'let ', 'var ', '=>', 'interface ',
                                      'type ', 'import {', 'export ']):
        if 'interface ' in content or 'type ' in content or ': string' in content or ': number' in content:
            return "typescript"
        return "javascript"

    # Markdown
    if content.startswith('#') and '\n' in content:
        return "markdown"

    # Default to text for unknown
    return "text"


def fix_markdown_file(filepath: Path) -> tuple[int, int]:
    """Fix code blocks in a markdown file. Returns (total_blocks, fixed_blocks)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    total_blocks = 0
    fixed_blocks = 0
    modified = False
    new_lines = []
    in_code_block = False
    block_start_index = -1
    block_content_lines = []

    for i, line in enumerate(lines):
        if line.strip().startswith('```'):
            if not in_code_block:
                # Opening fence
                fence_content = line.strip()[3:].strip()
                if fence_content == '':
                    # No language - mark for fixing
                    total_blocks += 1
                    in_code_block = True
                    block_start_index = len(new_lines)
                    block_content_lines = []
                    new_lines.append(line)  # Add for now, will replace later if needed
                else:
                    # Already has language
                    in_code_block = True
                    block_start_index = -1
                    new_lines.append(line)
            else:
                # Closing fence - ALWAYS add as-is, never add language specifier here
                if block_start_index >= 0:
                    # Fix the opening fence that we marked earlier
                    content = ''.join(block_content_lines)
                    language = detect_language(content)
                    new_lines[block_start_index] = f'```{language}\n'
                    fixed_blocks += 1
                    modified = True

                # Add closing fence exactly as-is (no language specifier)
                new_lines.append(line)
                in_code_block = False
                block_start_index = -1
                block_content_lines = []
        else:
            # Regular line or code block content
            new_lines.append(line)
            if in_code_block and block_start_index >= 0:
                # Collect content for language detection
                block_content_lines.append(line)

    # Only write if changes were made
    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

    return total_blocks, fixed_blocks


def main():
    """Fix all markdown files in the repository."""
    repo_root = Path(__file__).parent

    # Find all markdown files
    md_files = list(repo_root.glob('**/*.md'))

    print(f"Found {len(md_files)} markdown files")
    print()

    total_files_fixed = 0
    total_blocks_fixed = 0

    for md_file in sorted(md_files):
        # Skip node_modules and other common directories
        if any(part in md_file.parts for part in ['.git', 'node_modules', '.venv', 'venv']):
            continue

        total_blocks, fixed_blocks = fix_markdown_file(md_file)

        if fixed_blocks > 0:
            total_files_fixed += 1
            total_blocks_fixed += fixed_blocks
            rel_path = md_file.relative_to(repo_root)
            print(f"✓ {rel_path}: Fixed {fixed_blocks}/{total_blocks} code blocks")

    print()
    print(f"Summary: Fixed {total_blocks_fixed} code blocks across {total_files_fixed} files")


if __name__ == '__main__':
    main()
