# PraisonAIWP - Architecture Documentation

## Overview

**PraisonAIWP** is a Python-based WordPress content management framework designed to simplify and automate WordPress content operations via WP-CLI over SSH.

### Key Features

- **Simple CLI**: Only 5 core commands (`init`, `create`, `update`, `find`, `list`)
- **Smart Defaults**: Auto-detects file formats, execution modes, and optimal settings
- **Dual Execution Modes**: Sequential (Python) for reliability, Parallel (Node.js) for speed
- **Precision Editing**: Line-specific and occurrence-specific text replacements
- **Safe Operations**: Auto-backup, preview mode, dry-run capabilities

### Design Philosophy

1. **Convention Over Configuration** - Sensible defaults, minimal setup
2. **Safety First** - Preview, backup, confirm before destructive operations
3. **Performance When Needed** - Auto-parallel for bulk operations
4. **Developer Experience** - Clear commands, helpful errors, progress indicators

## System Architecture

```
User (CLI)
    ↓
CLI Layer (Click) → 5 Commands: init, create, update, find, list
    ↓
Operations Layer → Create, Update, Search Operations
    ↓
Core Layer → SSH Manager, WP Client, Content Editor
    ↓
Execution Modes → Sequential (Python) | Parallel (Node.js)
    ↓
Remote WordPress Server → WP-CLI, Database, WordPress Core
```

## Project Structure

```
praisonaiwp/
├── setup.py
├── requirements.txt
├── praisonaiwp/
│   ├── __init__.py
│   ├── core/              # SSH, WP-CLI, DB, REST API
│   ├── editors/           # Content editing logic
│   ├── operations/        # High-level operations
│   ├── cli/               # CLI commands
│   ├── parallel/          # Node.js bridge for parallel ops
│   └── utils/             # Logger, validator, backup, progress
├── templates/             # Content templates
├── tests/                 # Unit & integration tests
└── examples/              # Usage examples
```

## Core Components

### 1. SSH Manager (`core/ssh_manager.py`)
- Manages SSH connections using Paramiko
- Context manager support for auto-cleanup
- Connection pooling and retry logic

### 2. WP Client (`core/wp_client.py`)
- Wrapper around WP-CLI
- Handles different PHP binaries (Plesk support)
- Returns Python objects (not raw strings)

### 3. Content Editor (`editors/content_editor.py`)
- `replace_at_line()` - Replace at specific line number
- `replace_nth_occurrence()` - Replace 1st, 2nd, nth occurrence
- `replace_in_range()` - Replace in line range
- `find_occurrences()` - Find all matches with line numbers
- `preview_changes()` - Preview before applying

### 4. Operations Layer (`operations/`)
- **Create**: Single post, from file, from template, bulk
- **Update**: Content, with replacement (line/nth), bulk
- **Search**: Find in post, find in all posts, list posts

### 5. CLI Layer (`cli/`)
- Built with Click framework
- 5 commands: init, create, update, find, list
- Smart defaults and auto-detection

### 6. Parallel Executor (`parallel/`)
- Python-Node.js bridge for parallel operations
- Automatically used when >10 posts
- 10x faster for bulk operations

## CLI Commands

### 1. `praisonaiwp init`
Initialize configuration (one-time setup)

### 2. `praisonaiwp create [file|title]`
Create posts (auto-detects format, auto-parallel for bulk)

### 3. `praisonaiwp update <id> [find] [replace]`
Update posts with optional `--line` or `--nth` flags

### 4. `praisonaiwp find <pattern>`
Search for text in posts

### 5. `praisonaiwp list`
List WordPress posts with filters

## Configuration

**Location**: `~/.praisonaiwp/config.yaml`

```yaml
default_server: production

servers:
  production:
    hostname: example.com
    username: user
    key_file: ~/.ssh/id_ed25519
    wp_path: /var/www/html
    php_bin: /opt/plesk/php/8.3/bin/php

settings:
  auto_backup: true
  parallel_threshold: 10
  parallel_workers: 10
  log_level: INFO
```

## Data Flow Examples

### Create 100 Posts (Auto-Parallel)
```
User: praisonaiwp create posts.json
  ↓
Detect: 100 posts in file
  ↓
Auto-select: Parallel mode
  ↓
Spawn Node.js process
  ↓
Create 10 batches of 10 posts
  ↓
Execute batches in parallel
  ↓
Complete in ~8 seconds (vs 50s sequential)
```

### Update Specific Line
```
User: praisonaiwp update 123 "old" "new" --line 10
  ↓
Get post content
  ↓
Apply: ContentEditor.replace_at_line(content, 10, "old", "new")
  ↓
Preview changes (show diff)
  ↓
Backup original
  ↓
Confirm with user
  ↓
Update post
```

## Security

- SSH key-based authentication only
- No password storage
- Config file permissions: 600
- Automatic backup before destructive operations
- Preview mode for all changes

## Performance

- **Sequential**: ~0.5s per post (network limited)
- **Parallel (10 workers)**: ~5-8s for 100 posts
- **Speedup**: 10x faster for bulk operations

## Testing Strategy

- **Unit Tests**: Core components (SSH, WP Client, Content Editor)
- **Integration Tests**: CLI commands, end-to-end workflows
- **Fixtures**: Sample posts, config files
- **Mocking**: SSH connections for offline testing

## Future Enhancements

1. AI-powered content generation
2. WordPress REST API support (alternative to WP-CLI)
3. Plugin system for custom operations
4. Web dashboard for visual management
5. Multi-site support
6. Content migration tools
7. SEO optimization features

---

**Version**: 1.0.0  
**Last Updated**: October 2025


✅ SIMPLIFIED CLI STRUCTURE
1️⃣ Setup (One-time)
bash
# Initialize with interactive prompts
praisonaiwp init

# Asks:
# - Server hostname?
# - SSH username?
# - SSH key path? (default: ~/.ssh/id_ed25519)
# - WordPress path? (auto-detects)
# - PHP binary? (auto-detects)

# That's it! Saved to ~/.praisonaiwp/config.yaml
2️⃣ Create Posts
bash
# Single post (interactive)
praisonaiwp create
# Prompts for: title, content, status

# Single post (direct)
praisonaiwp create "My Post Title" --content "Post content"

# From file (auto-detects format: JSON, YAML, CSV)
praisonaiwp create posts.json

# 100 posts? Same command! Auto-parallel if >10 posts
praisonaiwp create 100_posts.json
# Automatically uses parallel mode for speed ⚡
3️⃣ Update Posts
bash
# Interactive mode
praisonaiwp update 123
# Shows current content, asks what to change

# Direct replacement
praisonaiwp update 123 "old text" "new text"

# Specific line
praisonaiwp update 123 "old text" "new text" --line 10

# Nth occurrence
praisonaiwp update 123 "old text" "new text" --nth 2

# Preview first (always safe)
praisonaiwp update 123 "old text" "new text" --preview
4️⃣ Find
bash
# Find in post
praisonaiwp find 123 "search text"

# Find across all posts
praisonaiwp find "search text"
5️⃣ List
bash
# List all posts
praisonaiwp list

# List pages
praisonaiwp list --type page

# List with search
praisonaiwp list --search "church"
🎯 EVEN SIMPLER: Natural Language Style
bash
# Create
praisonaiwp "create a post titled 'Hello World'"
praisonaiwp "create 100 posts from posts.json"

# Update
praisonaiwp "update post 123 replace 'old' with 'new' on line 10"
praisonaiwp "update post 123 change the 2nd occurrence of 'old' to 'new'"

# Find
praisonaiwp "find 'church' in post 123"
praisonaiwp "show me all posts with 'church'"

# List
praisonaiwp "list all pages"
praisonaiwp "show me published posts"
🏆 RECOMMENDED: Hybrid Approach
Simple commands + Smart defaults + Natural language fallback

Core Commands (5 only):
bash
praisonaiwp init              # Setup (one-time)
praisonaiwp create [file]     # Create posts
praisonaiwp update <id>       # Update posts
praisonaiwp find <pattern>    # Search
praisonaiwp list              # List posts
Smart Defaults:
Auto-detects file format (JSON/YAML/CSV)
Auto-uses parallel mode for bulk (>10 posts)
Auto-backups before updates
Auto-preview for destructive operations
Auto-connects to default server
Example Usage:
bash
# Setup once
praisonaiwp init

# Create single post
praisonaiwp create "My Post" --content "Hello World"

# Create 100 posts (auto-parallel!)
praisonaiwp create posts.json
# Output: Creating 100 posts in parallel... Done in 8s ⚡

# Update specific line
praisonaiwp update 123 "old" "new" --line 10
# Output: Preview changes? [Y/n]
#         Line 10: "old heading" → "new heading"
#         Apply? [Y/n]

# Find text
praisonaiwp find "church"
# Output: Found in 9 posts:
#         - Post 116 (line 10, 55)
#         - Post 117 (line 10)
#         ...
Comparison: Before vs After
❌ BEFORE (Too Complex):
bash
praisonaiwp bulk create \
  --server production \
  --file posts.json \
  --mode parallel \
  --workers 10 \
  --backup \
  --dry-run
✅ AFTER (Simple):
bash
praisonaiwp create posts.json
# Auto-detects: bulk, auto-parallel, auto-backup, auto-preview
File Format (Super Simple)
posts.json
json
[
  {
    "title": "Tamil Church in Peterborough",
    "content": "<p>Welcome...</p>"
  },
  {
    "title": "Hindi Church in Peterborough",
    "content": "<p>Welcome...</p>"
  }
]
updates.json
json
[
  {
    "id": 116,
    "line": 10,
    "find": "Old Heading",
    "replace": "New Heading"
  },
  {
    "id": 117,
    "line": 10,
    "find": "Old Heading",
    "replace": "Different Heading"
  }
]
🎯 Final Recommendation
Use this simplified structure:

bash
# 5 core commands only
praisonaiwp init
praisonaiwp create [file|title]
praisonaiwp update <id> [find] [replace]
praisonaiwp find <pattern>
praisonaiwp list

# Smart flags (optional)
--line <num>        # Update specific line
--nth <num>         # Update nth occurrence
--preview           # Preview changes
--no-backup         # Skip backup
--server <name>     # Use different server
Benefits:

✅ Only 5 commands to remember
✅ Smart defaults (no need to specify mode, workers, etc.)
✅ Auto-detects everything
✅ Interactive when needed
✅ Safe by default (preview, backup)
✅ Fast automatically (parallel for bulk)