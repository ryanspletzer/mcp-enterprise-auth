#!/bin/bash
# Check for code blocks without language specifiers (opening backticks only)

file="$1"
in_code=false
fence_length=0
line_num=0

while IFS= read -r line; do
  ((line_num++))

  # Match any number of backticks (3 or more)
  if [[ "$line" =~ ^(\`{3,})([a-zA-Z]*) ]]; then
    current_fence="${BASH_REMATCH[1]}"
    language="${BASH_REMATCH[2]}"
    current_length="${#current_fence}"

    if [ "$in_code" = false ]; then
      # Opening fence
      if [ -z "$language" ]; then
        echo "$file:$line_num: Code block without language specifier"
      fi
      in_code=true
      fence_length="$current_length"
    else
      # We're inside a code block - only consider fences that could close it
      # (same length or longer than the opening fence)
      if [ "$current_length" -ge "$fence_length" ]; then
        in_code=false
        fence_length=0
      fi
      # Shorter fences are content and should be ignored
    fi
  fi
done < "$file"
