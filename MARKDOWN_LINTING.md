# Markdown Linting

This repository enforces strict markdown linting rules to ensure consistent documentation quality.

## Configuration

Markdown linting is configured in `.markdownlint.json` with the following key rules:

- **MD001**: Heading levels increment by one at a time
- **MD003**: ATX-style headings (`#` syntax)
- **MD004**: Consistent list style (dash `-`)
- **MD007**: Unordered list indentation (2 spaces)
- **MD013**: Line length (disabled - no limit)
- **MD022**: Headings should be surrounded by blank lines
- **MD024**: Multiple headings with same content (siblings only)
- **MD025**: Single top-level heading
- **MD026**: No trailing punctuation in headings
- **MD029**: Ordered list item prefix (ordered style)
- **MD031**: Fenced code blocks should be surrounded by blank lines
- **MD032**: Lists should be surrounded by blank lines
- **MD033**: Limited inline HTML (only `<summary>`, `<details>`, `<br>`)
- **MD040**: **Fenced code blocks must specify language**
- **MD041**: First line must be top-level heading
- **MD046**: Fenced code block style (backticks)
- **MD048**: Code fence style (backtick)
- **MD060**: Tables should be pipe-delimited

## Code Block Language Requirements

**All code blocks MUST specify a language**,
even if it's just `text`:

````markdown
<!-- WRONG -->
```
some content
```

<!-- CORRECT -->
```text
some content
```

<!-- CORRECT - Common languages -->
```bash
echo "Shell commands"
```

```python
def example():
    pass
```

```json
{"key": "value"}
```

```yaml
key: value
```

```typescript
const x: string = "typed";
```
````

## Scripts

### `fix-markdown.py`

Automatically fixes code blocks without language specifiers (MD040 violations):

```bash
# Fix all markdown files
python3 fix-markdown.py
```

The script intelligently detects languages based on content:

- **bash**: Commands starting with `$`, `git`, `docker`, `npm`, `curl`, etc.
- **python**: Code with `def`, `class`, `import`, `async`, etc.
- **json**: Objects/arrays with colons
- **yaml**: Key-value pairs with colons
- **typescript**: Code with type annotations
- **text**: ASCII art, directory trees, logs, unknown content

### `fix-md032.py`

Automatically fixes MD032 violations - ensures lists are surrounded by blank lines:

```bash
# Fix all markdown files
python3 fix-md032.py
```

The script:

- Adds blank lines before lists that start without proper spacing
- Adds blank lines after lists that end without proper spacing
- Handles both unordered (`-`, `*`, `+`) and ordered (`1.`, `2.`) lists
- Skips content inside code blocks
- Reports number of violations fixed per file

### `fix-md031.py`

Automatically fixes MD031 violations - ensures fenced code blocks are surrounded by blank lines:

```bash
# Fix all markdown files
python3 fix-md031.py
```

The script:

- Adds blank lines before code blocks that start without proper spacing
- Adds blank lines after code blocks that end without proper spacing
- Handles both ` ``` ` and `~~~~` style fences
- Reports number of violations fixed per file

### `lint-markdown.sh`

Validates all markdown files against linting rules:

```bash
# Check all markdown files
./lint-markdown.sh
```

Requires `markdownlint-cli`:

```bash
npm install -g markdownlint-cli
```

### `check-md.sh`

Low-level checker for code blocks without language specifiers:

```bash
# Check a specific file
./check-md.sh README.md

# Check multiple files
for file in **/*.md; do ./check-md.sh "$file"; done
```

## IDE Integration

### VS Code

Install the **markdownlint extension**:

```bash
code --install-extension DavidAnson.vscode-markdownlint
```

The extension will automatically:

- Highlight linting violations
- Use `.markdownlint.json` configuration
- Provide quick fixes for some issues

### Other Editors

Most editors support markdownlint via plugins:

- **Vim/Neovim**: [ALE](https://github.com/dense-analysis/ale)
  or [coc-markdownlint](https://github.com/fannheyward/coc-markdownlint)
- **Emacs**: [flycheck-markdownlint](https://github.com/prosains/flycheck-markdownlint)
- **Sublime Text**:
  [SublimeLinter-contrib-markdownlint](https://github.com/jonlabelle/SublimeLinter-contrib-markdownlint)

## CI Integration

To enforce linting in CI/CD:

```yaml
# .github/workflows/lint.yml
name: Lint
on: [push, pull_request]
jobs:
  markdown:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm install -g markdownlint-cli
      - run: ./lint-markdown.sh
```

## Common Issues and Fixes

### Code Blocks Without Language

**Problem:**

````markdown
```
code here
```
````

**Fix:**

````markdown
```text
code here
```
````

### Inconsistent Heading Levels

**Problem:**

````markdown
# Main Title

### Skipped H2
````

**Fix:**

````markdown
# Main Title

## Section

### Subsection
````

### Trailing Punctuation in Headings

**Problem:**

````markdown
## Installation:
````

**Fix:**

````markdown
## Installation
````

### Multiple Top-Level Headings

**Problem:**

````markdown
# Title One

# Title Two
````

**Fix:**

````markdown
# Title One

## Section Two
````

## Manual Override

To disable a rule for a specific file,
add a comment at the top:

````markdown
<!-- markdownlint-disable MD013 -->

# Very Long Title That Exceeds Normal Line Length Limits But Is Necessary
````

To disable a rule for a specific line:

````markdown
<!-- markdownlint-disable-next-line MD033 -->
<div>Custom HTML element</div>
````

## Summary

- All code blocks have language specifiers
- Consistent heading hierarchy
- Consistent list formatting
- ATX-style headings
- Single top-level heading per file
- Limited inline HTML

Run `python3 fix-markdown.py`, `python3 fix-md032.py`, and `python3 fix-md031.py` to auto-fix most issues,
then `./lint-markdown.sh` to validate.
