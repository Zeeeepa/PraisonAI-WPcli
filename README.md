# PraisonAIWP

AI-powered WordPress content management framework with precision editing capabilities.

## Features

- 🚀 **Simple CLI** - Only 5 core commands to remember
- ⚡ **Fast** - Auto-parallel mode for bulk operations (10x faster)
- 🎯 **Precise** - Line-specific and occurrence-specific text replacements
- 🔒 **Safe** - Auto-backup, preview mode, dry-run capabilities
- 🌐 **Multi-Server** - Manage multiple WordPress installations
- 📝 **Smart** - Auto-detects file formats and optimal settings

## Installation

### Using uv (Recommended - 10x faster!)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone https://github.com/yourusername/praisonaiwp
cd praisonaiwp
uv sync

# Run commands
uv run praisonaiwp init
```

### Using pip

```bash
pip install praisonaiwp

# Or install from source
git clone https://github.com/yourusername/praisonaiwp
cd praisonaiwp
pip install -e .
```

## Quick Start

### 1. Initialize Configuration

```bash
praisonaiwp init
```

This will prompt you for:
- Server hostname
- SSH username
- SSH key path
- WordPress path (auto-detected)
- PHP binary (auto-detected)

### 2. Create Posts

```bash
# Single post
praisonaiwp create "My Post Title" --content "Post content here"

# From file (auto-detects JSON/YAML/CSV)
praisonaiwp create posts.json

# Create 100 posts (automatically uses parallel mode!)
praisonaiwp create 100_posts.json
```

### 3. Update Posts

```bash
# Update all occurrences
praisonaiwp update 123 "old text" "new text"

# Update specific line only
praisonaiwp update 123 "old text" "new text" --line 10

# Update 2nd occurrence only
praisonaiwp update 123 "old text" "new text" --nth 2

# Preview changes first
praisonaiwp update 123 "old text" "new text" --preview
```

### 4. Find Text

```bash
# Find in specific post
praisonaiwp find "search text" 123

# Find across all posts
praisonaiwp find "search text"

# Find in pages
praisonaiwp find "search text" --type page
```

### 5. List Posts

```bash
# List all posts
praisonaiwp list

# List pages
praisonaiwp list --type page

# List drafts
praisonaiwp list --status draft
```

## File Formats

### JSON Format

```json
[
  {
    "title": "Post Title",
    "content": "<p>Post content</p>",
    "status": "publish",
    "type": "post"
  }
]
```

### YAML Format

```yaml
- title: Post Title
  content: <p>Post content</p>
  status: publish
  type: post
```

### CSV Format

```csv
title,content,status,type
"Post Title","<p>Post content</p>",publish,post
```

## Configuration

Configuration is stored in `~/.praisonaiwp/config.yaml`:

```yaml
version: "1.0"
default_server: default

servers:
  default:
    hostname: example.com
    username: user
    key_file: ~/.ssh/id_ed25519
    port: 22
    wp_path: /var/www/html
    php_bin: /opt/plesk/php/8.3/bin/php
    wp_cli: /usr/local/bin/wp

settings:
  auto_backup: true
  parallel_threshold: 10
  parallel_workers: 10
  ssh_timeout: 30
  log_level: INFO
```

## Advanced Usage

### Line-Specific Replacement

When the same text appears multiple times but you only want to replace it at a specific line:

```bash
# Replace only at line 10
praisonaiwp update 123 "Welcome" "Peterborough Church" --line 10
```

### Occurrence-Specific Replacement

Replace only the 1st, 2nd, or nth occurrence:

```bash
# Replace only the 2nd occurrence
praisonaiwp update 123 "Welcome" "Peterborough Church" --nth 2
```

### Bulk Operations

Create 100 posts in ~8 seconds (vs 50+ seconds sequential):

```bash
# Automatically uses parallel mode for files with >10 posts
praisonaiwp create 100_posts.json
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed technical documentation.

## Development

```bash
# Clone repository
git clone https://github.com/yourusername/praisonaiwp
cd praisonaiwp

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=praisonaiwp

# Format code
black praisonaiwp/

# Lint
flake8 praisonaiwp/
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details.

## Author

Praison

## Links

- GitHub: https://github.com/yourusername/praisonaiwp
- Documentation: https://praisonaiwp.readthedocs.io
- PyPI: https://pypi.org/project/praisonaiwp
