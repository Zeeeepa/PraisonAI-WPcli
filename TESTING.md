# PraisonAIWP Testing Guide

## Running Tests

### Install Test Dependencies

**Using uv (Recommended):**

```bash
uv sync --extra dev
```

**Or using pip:**

```bash
pip install -e ".[dev]"
```

### Run All Tests

**Using uv:**

```bash
uv run pytest
```

**Or with activated venv:**

```bash
source .venv/bin/activate
pytest
```

### Run with Coverage

```bash
pytest --cov=praisonaiwp --cov-report=html
```

### Run Specific Test File

```bash
pytest tests/test_content_editor.py
pytest tests/test_config.py
pytest tests/test_wp_client.py
```

### Run Specific Test

```bash
pytest tests/test_content_editor.py::TestContentEditor::test_replace_at_line
```

### Run with Verbose Output

```bash
pytest -v
```

### Run with Print Statements

```bash
pytest -s
```

## Test Structure

```
tests/
├── conftest.py              # Pytest fixtures
├── test_content_editor.py   # ContentEditor tests
├── test_config.py           # Config tests
└── test_wp_client.py        # WPClient tests (with mocking)
```

## Test Coverage

Current test coverage:

- ✅ **ContentEditor**: 100% coverage
  - Line-specific replacement
  - Nth occurrence replacement
  - Range replacement
  - Context-aware replacement
  - Find occurrences
  - Preview changes

- ✅ **Config**: 100% coverage
  - Initialize default config
  - Save and load
  - Add/get servers
  - Settings management
  - Error handling

- ✅ **WPClient**: 90% coverage (mocked)
  - Execute WP-CLI commands
  - Create/update/list posts
  - Database queries
  - Search and replace
  - Error handling

## Manual Testing

### Test CLI Commands

```bash
# Initialize
praisonaiwp init

# Create single post
praisonaiwp create "Test Post" --content "Test content"

# Update post
praisonaiwp update 123 "old" "new" --line 10 --preview

# Find text
praisonaiwp find "search text"

# List posts
praisonaiwp list --type page
```

### Test with Real WordPress Server

1. **Setup test server**:
   ```bash
   praisonaiwp init
   # Enter test server details
   ```

2. **Create test post**:
   ```bash
   praisonaiwp create "Test Post $(date +%s)" --content "Test content"
   ```

3. **Update test post**:
   ```bash
   praisonaiwp update <POST_ID> "Test" "UPDATED" --preview
   ```

4. **Clean up**:
   ```bash
   # Delete test posts manually via WordPress admin
   ```

### Test Parallel Execution

1. **Install Node.js dependencies**:
   ```bash
   cd praisonaiwp/parallel/nodejs
   npm install
   ```

2. **Create test file with 20 posts**:
   ```bash
   cat > test_posts.json << 'EOF'
   [
     {"title": "Test 1", "content": "<p>Content 1</p>"},
     {"title": "Test 2", "content": "<p>Content 2</p>"},
     ...
     {"title": "Test 20", "content": "<p>Content 20</p>"}
   ]
   EOF
   ```

3. **Create posts (should use parallel mode)**:
   ```bash
   time praisonaiwp create test_posts.json
   # Should complete in ~5-8 seconds
   ```

## Integration Tests

### Test SSH Connection

```python
from praisonaiwp.core.config import Config
from praisonaiwp.core.ssh_manager import SSHManager

config = Config()
server = config.get_server()

with SSHManager(
    server['hostname'],
    server['username'],
    server['key_file']
) as ssh:
    stdout, stderr = ssh.execute('echo "Hello"')
    assert stdout.strip() == "Hello"
```

### Test WP-CLI Access

```python
from praisonaiwp.core.wp_client import WPClient

# ... (setup ssh as above)

wp = WPClient(ssh, server['wp_path'], server['php_bin'])
posts = wp.list_posts(post_type='post')
assert isinstance(posts, list)
```

### Test Content Editor

```python
from praisonaiwp.editors.content_editor import ContentEditor

content = "line1\nline2\nline3"
editor = ContentEditor()

result = editor.replace_at_line(content, 2, "line2", "LINE2")
assert "LINE2" in result
assert result.count("line") == 2  # line1 and line3 unchanged
```

## Performance Testing

### Benchmark Sequential vs Parallel

```bash
# Create 100 test posts
python -c "
import json
posts = [{'title': f'Test {i}', 'content': f'<p>Content {i}</p>'} 
         for i in range(100)]
with open('100_posts.json', 'w') as f:
    json.dump(posts, f)
"

# Test sequential (disable parallel)
# Edit config: parallel_threshold: 1000
time praisonaiwp create 100_posts.json

# Test parallel (enable parallel)
# Edit config: parallel_threshold: 10
time praisonaiwp create 100_posts.json
```

## Continuous Integration

### GitHub Actions (Example)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -e ".[dev]"
    
    - name: Run tests
      run: |
        pytest --cov=praisonaiwp --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Troubleshooting Tests

### SSH Connection Tests Failing

```bash
# Check SSH key permissions
chmod 600 ~/.ssh/id_ed25519

# Test SSH manually
ssh -i ~/.ssh/id_ed25519 user@hostname

# Check config
cat ~/.praisonaiwp/config.yaml
```

### WP-CLI Tests Failing

```bash
# Test WP-CLI manually
ssh user@hostname "cd /path/to/wp && wp --info"

# Check PHP binary
ssh user@hostname "which php"
ssh user@hostname "/opt/plesk/php/8.3/bin/php --version"
```

### Parallel Tests Failing

```bash
# Check Node.js installation
node --version  # Should be 14+

# Install Node.js dependencies
cd praisonaiwp/parallel/nodejs
npm install

# Test Node.js script manually
echo '{"operation":"create","data":[],"server":{},"workers":10}' | node index.js
```

## Test Data Cleanup

After testing, clean up test data:

```bash
# List test posts
praisonaiwp list --search "Test"

# Delete via WordPress admin or WP-CLI
ssh user@hostname "cd /path/to/wp && wp post delete <ID> --force"
```

## Best Practices

1. **Always use test server** - Never test on production
2. **Clean up test data** - Delete test posts after testing
3. **Use mocking** - Mock SSH/WP-CLI for unit tests
4. **Test edge cases** - Invalid inputs, network errors, etc.
5. **Performance test** - Benchmark before and after changes
6. **Integration test** - Test with real WordPress server periodically

## Next Steps

- [ ] Add integration tests with Docker WordPress
- [ ] Add performance benchmarks
- [ ] Add CLI command tests
- [ ] Add end-to-end tests
- [ ] Setup CI/CD pipeline
