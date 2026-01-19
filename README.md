# SonarCloud-GitHub Sync CLI

A command-line tool that synchronizes issues between SonarCloud and GitHub, automatically creating GitHub issues for SonarCloud issues and maintaining bidirectional sync of issue states.

## Features

- **Automatic Issue Creation**: Creates GitHub issues for new SonarCloud issues
- **Bidirectional Sync**: Syncs issue states between SonarCloud and GitHub
- **Duplicate Prevention**: Avoids creating duplicate GitHub issues
- **Configurable Filtering**: Filter issues by type (BUG, VULNERABILITY, CODE_SMELL)
- **Dry Run Mode**: Preview changes without making modifications
- **Rich CLI Interface**: Clear progress reporting and error handling

## Installation

```bash
# Install the package in development mode
pip install -e ".[dev]"

# Install pre-commit hooks (for development)
pre-commit install
```

## Configuration

Set the following environment variables:

```bash
export SONAR_TOKEN="your-sonarcloud-token"
export GITHUB_TOKEN="your-github-token"
```

### Getting Tokens

#### SonarCloud Token
1. Go to [SonarCloud](https://sonarcloud.io)
2. Navigate to **My Account** → **Security**
3. Click **Generate Token**
4. Provide a name for your token and click **Generate**
5. Copy and securely store the generated token

#### GitHub Token (Least Privilege Configuration)

For security best practices, create a GitHub Personal Access Token with minimal required permissions:

**For Public Repositories:**
1. Go to GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. Click **Generate new token** → **Generate new token (classic)**
3. Set an appropriate expiration date
4. Select **only** these scopes:
   - `public_repo` - Access public repositories (allows reading and writing to public repository issues)

**For Private Repositories:**
1. Follow the same steps as above
2. Select **only** these scopes:
   - `repo` - Full control of private repositories (includes issues access)

**Required Token Permissions Summary:**
- **Read Access**: View repository information, read existing issues
- **Write Access**: Create new issues, update issue state (open/close), add labels
- **Issues Access**: Full CRUD operations on repository issues

**Alternative: Fine-grained Personal Access Tokens (Beta)**
For even more granular control, you can use GitHub's fine-grained tokens:
1. Go to **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens**
2. Click **Generate new token**
3. Set **Repository access** to specific repositories
4. Under **Repository permissions**, grant:
   - **Issues**: Read and write
   - **Metadata**: Read (required for repository access)

**Security Recommendations:**
- Set token expiration to the shortest practical timeframe
- Regularly rotate tokens
- Store tokens securely (environment variables, secrets management)
- Never commit tokens to version control
- Use repository-specific tokens when possible
- Monitor token usage in GitHub's audit logs

## Usage

### Basic Usage

```bash
sonarcloud-github-sync --sonar-project my-org_my-project --github-repo myorg/myrepo
```

### Advanced Usage

```bash
# Sync only specific issue types
sonarcloud-github-sync \
  --sonar-project my-org_my-project \
  --github-repo myorg/myrepo \
  --issue-types BUG,VULNERABILITY

# Preview changes without making them (dry run)
sonarcloud-github-sync \
  --sonar-project my-org_my-project \
  --github-repo myorg/myrepo \
  --dry-run
```

### CLI Options

- `--sonar-project`: SonarCloud project key (required)
- `--github-repo`: GitHub repository in format 'owner/repo' (required)
- `--issue-types`: Comma-separated list of issue types to sync (default: BUG,VULNERABILITY,CODE_SMELL)
- `--dry-run`: Show what would be done without making changes
- `--debug`: Enable debug logging with detailed output
- `--log-level`: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) - default: INFO
- `--help`: Show help message

## GitHub Action

You can run the sync from other repositories using this GitHub Action.

### Action Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `sonar_project` | yes | — | SonarCloud project key (e.g., `my-org_my-project`) |
| `issue_types` | no | `BUG,VULNERABILITY,CODE_SMELL` | Comma-separated list of issue types to sync |
| `dry_run` | no | `false` | Preview changes without making modifications |
| `log_level` | no | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `debug` | no | `false` | Enable debug logging |
| `python_version` | no | `3.11` | Python version to use |

### Action Secrets

Composite actions pass secrets via environment variables. The action supports two approaches:

**Recommended: Workflow Permissions (no explicit secret needed)**
- The action automatically uses `github.token` with workflow permissions
- Simply grant `permissions: { issues: write }` in the calling job

**Alternative: Explicit GitHub Token**
- Pass `GITHUB_TOKEN` via env if you need a custom token (PAT, bot token, etc.)
- Useful for cross-repo access or elevated permissions

| Environment Variable | Required | Default | Description |
|----------------------|----------|---------|-------------|
| `SONAR_TOKEN` | yes | — | SonarCloud personal access token |
| `GITHUB_TOKEN` | no | `github.token` | GitHub token with `issues:write` permission; defaults to workflow token |

### Example Usage: With Workflow Permissions (Recommended)

```yaml
name: SonarCloud Sync

on:
  workflow_dispatch:
  schedule:
    - cron: '0 0 * * 1'  # Weekly on Mondays

jobs:
  sync:
    runs-on: ubuntu-latest
    permissions:
      issues: write
      contents: read
    steps:
      - uses: Gorton218/sonarqube-to-github-issue-sync@main
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
        with:
          sonar_project: my-org_my-project
          issue_types: BUG,VULNERABILITY,CODE_SMELL
          dry_run: false
          log_level: INFO
          debug: false
```

### Example Usage: With Custom GitHub Token

If you need to use a custom GitHub token (PAT, bot token, etc.) for cross-repo access or elevated permissions:

```yaml
- uses: Gorton218/sonarqube-to-github-issue-sync@main
  env:
    SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
    GITHUB_TOKEN: ${{ secrets.CUSTOM_GITHUB_TOKEN }}
  with:
    sonar_project: my-org_my-project
```

### Example Usage: With Dry Run

Preview changes before applying them:

```yaml
- uses: Gorton218/sonarqube-to-github-issue-sync@main
  env:
    SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
  with:
    sonar_project: my-org_my-project
    dry_run: true
    debug: true
```

### Action Notes

- **Repository Auto-Discovery**: The action automatically uses `github.repository`, so no `github_repo` input is needed.
- **Permissions**: The calling job must have `permissions: { issues: write }` to allow issue creation/updates.
- **Versioning**: Use a tagged ref (e.g., `@v1`) for stable releases; use `@main` for the latest development version.
- **Token Default**: If `GITHUB_TOKEN` is not provided in `env`, the action defaults to `github.token` from workflow permissions.
- **Scheduling**: Consider running the sync on a schedule (e.g., weekly) to keep issues in sync automatically.

### Debug and Logging Options

For troubleshooting and detailed operation tracking:

```bash
# Enable debug mode with verbose logging
sonarcloud-github-sync \
  --sonar-project my-org_my-project \
  --github-repo myorg/myrepo \
  --debug

# Set specific log level
sonarcloud-github-sync \
  --sonar-project my-org_my-project \
  --github-repo myorg/myrepo \
  --log-level DEBUG

# Combine with dry run for detailed preview
sonarcloud-github-sync \
  --sonar-project my-org_my-project \
  --github-repo myorg/myrepo \
  --debug \
  --dry-run
```

**Debug mode provides:**
- Detailed API request/response logging
- Step-by-step operation tracking
- Configuration validation details
- Error stack traces with file locations
- Timing information for operations

## How It Works

### SonarCloud → GitHub Sync

1. Fetches open issues from the specified SonarCloud project
2. Filters issues by the configured types
3. Checks if a GitHub issue already exists for each SonarCloud issue
4. Creates new GitHub issues for SonarCloud issues that don't have corresponding GitHub issues
5. Closes GitHub issues when their corresponding SonarCloud issues are resolved

### GitHub → SonarCloud Sync

1. Fetches GitHub issues with the "sonarcloud" label
2. For closed GitHub issues with state reason "not_planned", marks the corresponding SonarCloud issue as "Won't Fix"
3. Ignores GitHub issues closed with state reason "completed"

### Issue Mapping

- **Title**: GitHub issue title matches SonarCloud issue message
- **Body**: Contains SonarCloud issue details and permanent link
- **Labels**: Includes "sonarcloud" label plus any existing SonarCloud tags
- **Unique Identifier**: SonarCloud issue link in GitHub issue body prevents duplicates

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_sync.py
```

### Code Quality

```bash
# Format code
black src tests

# Lint code
flake8 src tests

# Type checking
mypy src
```

### Project Structure

```
src/sonarcloud_github_sync/
├── __init__.py          # Package initialization
├── cli.py              # Command-line interface
├── config.py           # Configuration management
├── github_client.py    # GitHub API client
├── sonar_client.py     # SonarCloud API client
└── sync.py             # Core synchronization logic

tests/
├── test_cli.py         # CLI tests
├── test_config.py      # Configuration tests
├── test_github_client.py # GitHub client tests
├── test_sonar_client.py  # SonarCloud client tests
├── test_sync.py        # Sync engine tests
└── test_integration.py # Integration tests
```

## Error Handling

The tool provides clear error messages for common issues:

- **Authentication Errors**: Invalid or missing tokens
- **API Errors**: Network issues, rate limiting, permission problems
- **Configuration Errors**: Invalid project keys or repository names

### Troubleshooting

**Common Issues and Solutions:**

1. **Authentication Failed**
   ```bash
   # Enable debug mode to see detailed auth flow
   sonarcloud-github-sync --debug --sonar-project PROJECT --github-repo REPO
   ```
   - Verify token environment variables are set correctly
   - Check token permissions and expiration
   - Test tokens individually with GitHub/SonarCloud web interfaces

2. **No Issues Found**
   ```bash
   # Debug issue filtering and retrieval
   sonarcloud-github-sync --debug --log-level DEBUG --sonar-project PROJECT --github-repo REPO
   ```
   - Verify SonarCloud project key format
   - Check if issues exist with specified types
   - Review issue type filtering (BUG, VULNERABILITY, CODE_SMELL)

3. **API Rate Limiting**
   - The tool includes built-in retry logic
   - Debug mode shows rate limit headers
   - Consider running sync less frequently for large projects

4. **Permission Denied**
   ```bash
   # Check token permissions
   sonarcloud-github-sync --debug --dry-run --sonar-project PROJECT --github-repo REPO
   ```
   - Verify GitHub token has `repo` or `public_repo` scope
   - Ensure SonarCloud token has project access
   - Check repository visibility and access rights

**Debug Output Levels:**
- `INFO`: Basic operation progress and results
- `DEBUG`: Detailed API calls, data processing, and internal state
- With `--debug` flag: Maximum verbosity including stack traces

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and ensure code quality checks pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
