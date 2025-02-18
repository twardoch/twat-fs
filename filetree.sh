#!/usr/bin/env bash
# this_file: filetree.sh

# Create/overwrite the file with YAML frontmatter
cat >.cursor/rules/filetree.mdc <<'EOL'
---
description: File tree of the project
globs: 
---
EOL

# Append tree output to the file
tree -a -I ".git" --gitignore -n -h -I "*_cache" >>.cursor/rules/filetree.mdc
