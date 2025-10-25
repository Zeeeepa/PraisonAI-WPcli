# PraisonAIWP with UV Package Manager

This project uses **uv** - a fast, modern Python package manager built in Rust that's 10-100x faster than pip.

## Why UV?

- ⚡ **10-100x faster** than pip/poetry
- 🔒 **Lockfile support** for reproducible builds
- 🎯 **Single tool** for environments and dependencies
- 🚀 **Built in Rust** for maximum performance
- 📦 **Drop-in replacement** for pip, poetry, pipenv

## Installation

### Install UV

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv

# Or with homebrew
brew install uv
```

### Verify Installation

```bash
uv --version
```

## Quick Start

### 1. Sync Dependencies

```bash
# Install all dependencies (creates .venv automatically)
uv sync

# Install with dev dependencies
uv sync --extra dev
```

### 2. Activate Virtual Environment

```bash
# Activate the virtual environment
source .venv/bin/activate

# Or use uv run (no activation needed)
uv run praisonaiwp --help
```

### 3. Run Commands

```bash
# Run without activating venv
uv run praisonaiwp init

# Or activate venv first
source .venv/bin/activate
praisonaiwp init
```

## Development Workflow

### Install in Development Mode

```bash
# Sync all dependencies including dev tools
uv sync --extra dev

# Or install in editable mode
uv pip install -e .
```

### Add New Dependencies

```bash
# Add a new dependency
uv add requests

# Add a dev dependency
uv add --dev pytest

# Add with version constraint
uv add "click>=8.0"
```

### Remove Dependencies

```bash
uv remove requests
```

### Update Dependencies

```bash
# Update all dependencies
uv sync --upgrade

# Update specific package
uv add --upgrade click
```

### Run Tests

```bash
# Run tests with uv
uv run pytest

# Run with coverage
uv run pytest --cov=praisonaiwp

# Run specific test
uv run pytest tests/test_content_editor.py
```

### Run Scripts

```bash
# Run Python scripts
uv run python examples/create_single_post.py

# Run CLI commands
uv run praisonaiwp create "Test Post" --content "Hello"
```

### Format and Lint

```bash
# Format code with black
uv run black praisonaiwp/

# Lint with ruff
uv run ruff check praisonaiwp/

# Type check with mypy
uv run mypy praisonaiwp/
```

## Project Structure

```
praisonaiwp/
├── pyproject.toml       # Project configuration (replaces setup.py + requirements.txt)
├── .python-version      # Python version for the project
├── uv.lock              # Lockfile for reproducible builds (auto-generated)
├── .venv/               # Virtual environment (auto-created by uv)
└── praisonaiwp/         # Source code
```

## Common Commands

### Environment Management

```bash
# Create/sync environment
uv sync

# Remove environment
rm -rf .venv

# Recreate environment
uv sync --reinstall
```

### Dependency Management

```bash
# Show installed packages
uv pip list

# Show dependency tree
uv pip tree

# Export requirements
uv pip freeze > requirements.txt
```

### Python Version Management

```bash
# Use specific Python version
uv python install 3.11

# Pin Python version
echo "3.11" > .python-version
```

## Migration from pip/poetry

### From pip (requirements.txt)

```bash
# Install from requirements.txt
uv pip install -r requirements.txt

# Or migrate to pyproject.toml
uv add $(cat requirements.txt)
```

### From poetry

```bash
# uv reads pyproject.toml automatically
uv sync

# Poetry commands → uv commands
poetry install → uv sync
poetry add pkg → uv add pkg
poetry run cmd → uv run cmd
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        uses: astral-sh/setup-uv@v2
      
      - name: Set up Python
        run: uv python install
      
      - name: Install dependencies
        run: uv sync --extra dev
      
      - name: Run tests
        run: uv run pytest --cov
```

### Docker

```dockerfile
FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
WORKDIR /app
COPY . .

# Install dependencies
RUN uv sync --frozen

# Run application
CMD ["uv", "run", "praisonaiwp"]
```

## Performance Comparison

| Operation | pip | poetry | uv |
|-----------|-----|--------|-----|
| Install 100 packages | 60s | 45s | **3s** |
| Create venv | 5s | 8s | **0.5s** |
| Resolve dependencies | 30s | 25s | **1s** |

## Troubleshooting

### UV not found

```bash
# Reinstall uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH
export PATH="$HOME/.cargo/bin:$PATH"
```

### Dependencies not syncing

```bash
# Clear cache and reinstall
uv cache clean
uv sync --reinstall
```

### Python version mismatch

```bash
# Install correct Python version
uv python install 3.11

# Verify
uv run python --version
```

## Advanced Usage

### Workspaces

```toml
# pyproject.toml
[tool.uv.workspace]
members = ["packages/*"]
```

### Custom Index

```bash
# Use custom PyPI index
uv pip install --index-url https://custom.pypi.org/simple package
```

### Offline Mode

```bash
# Install from cache only
uv sync --offline
```

## Resources

- **Official Docs**: https://docs.astral.sh/uv/
- **GitHub**: https://github.com/astral-sh/uv
- **Changelog**: https://github.com/astral-sh/uv/releases

## Quick Reference

```bash
# Setup
uv sync                          # Install dependencies
uv sync --extra dev              # Install with dev dependencies

# Run
uv run praisonaiwp init          # Run CLI command
uv run python script.py          # Run Python script
uv run pytest                    # Run tests

# Manage
uv add package                   # Add dependency
uv remove package                # Remove dependency
uv sync --upgrade                # Update all dependencies

# Environment
source .venv/bin/activate        # Activate venv (optional)
uv pip list                      # List packages
uv pip tree                      # Show dependency tree
```

---

**Note**: All previous `pip install` commands can be replaced with `uv sync` or `uv add`. The project is fully compatible with both workflows.
