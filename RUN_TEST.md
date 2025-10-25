# Run Real-World Server Test

## Quick Test

```bash
cd /Users/praison/crawler/praisonaiwp

# Install dependencies with uv
uv sync

# Run the test
uv run python test_real_server.py
```

## What the Test Does

1. **Tests SSH Connection** to your WordPress server
2. **Tests WP-CLI Access** with Plesk PHP
3. **Creates Test Post** (as draft for safety)
4. **Tests Line-Specific Update** - Updates line 2 only, leaves other occurrences unchanged
5. **Verifies Update** - Confirms only line 2 was changed
6. **Cleanup** - Optionally deletes test post

## Expected Output

```
═══════════════════════════════════════════════════
  PraisonAIWP Real-World Server Test
═══════════════════════════════════════════════════

Step 1: Testing SSH Connection
✓ Connected to your-server.com
✓ Command execution working: Hello from PraisonAIWP

Step 2: Testing WP-CLI Access
✓ WP-CLI is working

Step 3: Creating Test Post
Creating test post...
✓ Test post created successfully!
Post ID: 123
Title: PraisonAIWP Test Post
Status: draft
Type: post

Step 4: Testing Line-Specific Update
Fetching post content...
Found 2 occurrence(s) of 'Test Post from PraisonAIWP':
  Line 2: <h2>Test Post from PraisonAIWP</h2>
  Line 12: <h2>Test Post from PraisonAIWP</h2>

Replacing text at line 2 only...
✓ Post updated successfully!

Verifying update...
After update, found 1 occurrence(s) of original text:
  Line 12: <h2>Test Post from PraisonAIWP</h2>
✓ Found 1 occurrence(s) of updated text

✓ Line-specific update test PASSED!
Line 2 was updated, other occurrences remain unchanged

Step 5: Cleanup
Delete test post? (y/n):
```

## Manual Test Commands

If you want to test manually with CLI:

```bash
# Initialize config
uv run praisonaiwp init

# Create test post
uv run praisonaiwp create "Test Post" --content "<p>Test content</p>" --status draft

# Find text in post
uv run praisonaiwp find "Test" 123

# Update specific line
uv run praisonaiwp update 123 "old" "new" --line 2 --preview

# List posts
uv run praisonaiwp list --type post --status draft
```

## Troubleshooting

### SSH Key Permission Error
```bash
chmod 600 ~/.ssh/id_ed25519
```

### WP-CLI Not Found
The test uses the correct Plesk PHP path:
- PHP: `/opt/plesk/php/8.3/bin/php`
- WP-CLI: `/usr/local/bin/wp`

### Connection Timeout
Check firewall/SSH access to your server
