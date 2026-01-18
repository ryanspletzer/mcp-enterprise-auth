#!/bin/bash
# Verify all markdown files have language specifiers on code blocks

errors=0
total_files=0

for file in $(find . -name "*.md" -not -path "*/node_modules/*" -not -path "*/.git/*"); do
  ((total_files++))

  # Use check-md.sh to find violations (handles nested fences correctly)
  violations=$(./check-md.sh "$file")
  if [ -n "$violations" ]; then
    echo "$violations"
    error_count=$(echo "$violations" | wc -l)
    errors=$((errors + error_count))
  fi
done

echo ""
if [ $errors -eq 0 ]; then
  echo "✅ All $total_files markdown files have language specifiers on code blocks"
  exit 0
else
  echo "❌ Found $errors code blocks without language specifiers"
  exit 1
fi
