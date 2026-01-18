# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a CLI tool that synchronizes issues between SonarCloud and GitHub. The tool automatically creates GitHub issues for SonarCloud issues and maintains bidirectional sync of issue states. Key functionality includes:

- Creating GitHub issues from SonarCloud issues with proper mapping of titles, bodies, and labels
- Closing GitHub issues when corresponding SonarCloud issues are resolved
- Marking SonarCloud issues as "Won't Fix" when GitHub issues are closed as "Not Planned"
- Filtering issues by type (BUG, VULNERABILITY, etc.)
- Duplicate prevention using SonarCloud issue links as unique identifiers

## Architecture

The application follows a modular design with these core components:

1. **CLI Interface**: Command-line argument parsing with support for issue type filtering (`--issue-types=BUG,VULNERABILITY`)
2. **API Clients**: Separate modules for GitHub and SonarCloud API interactions
3. **Synchronization Logic**: Core business logic handling bidirectional sync between platforms
4. **Configuration**: Environment variable-based authentication (SONAR_TOKEN, GITHUB_TOKEN)

## Key Requirements

- **Authentication**: Must authenticate with both SonarCloud and GitHub APIs with fast-fail on invalid credentials
- **Duplicate Prevention**: Uses SonarCloud issue links in GitHub issue bodies as unique identifiers
- **State Mapping**: 
  - GitHub "Not Planned" closure → SonarCloud "Won't Fix"
  - GitHub "Completed" closure → No action on SonarCloud
  - SonarCloud resolved → GitHub issue closed
- **Labels**: All created GitHub issues must include a "sonarcloud" label plus any existing SonarCloud tags
- **Filtering**: Configurable issue type filtering with all types synced by default

## Development Commands

**Setup:**
```bash
# Install the package in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

**Development:**
```bash
# Run the CLI tool
sonarcloud-github-sync --sonar-project PROJECT_KEY --github-repo OWNER/REPO

# Run with specific issue types
sonarcloud-github-sync --sonar-project PROJECT_KEY --github-repo OWNER/REPO --issue-types BUG,VULNERABILITY

# Dry run to see what would happen
sonarcloud-github-sync --sonar-project PROJECT_KEY --github-repo OWNER/REPO --dry-run
```

**Testing:**
```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_sync.py
```

**Code Quality:**
```bash
# Format code
black src tests

# Lint code
flake8 src tests

# Type checking
mypy src
```

**Required Environment Variables:**
- `SONAR_TOKEN`: SonarCloud personal access token
- `GITHUB_TOKEN`: GitHub personal access token

## Implementation Notes

- The GitHub API client needs functions for: fetching issues by label, creating issues, closing issues, and querying close reasons
- The SonarCloud API client needs functions for: fetching project issues and transitioning issue states
- Core sync logic should handle both directions: SonarCloud→GitHub and GitHub→SonarCloud
- Error handling must provide clear, actionable messages for API failures, network errors, and rate limits
- Console logging should show progress like "Found 15 issues in SonarCloud", "Creating new issue for SC-123"

## Testing Strategy

- Unit tests for both API clients with mocked network requests
- Tests for core synchronization logic including edge cases like duplicate detection and state transitions
- Test coverage for error scenarios and edge cases

## Development Guidelines

**IMPORTANT**: When working with Python projects that have a `pyproject.toml` file:
- Always use the proper pyproject.toml configuration for package installation
- NEVER use workarounds like PYTHONPATH manipulation to bypass packaging issues
- If editable installs fail, fix the pyproject.toml configuration properly
- The build system should support PEP 660 for editable installs
- Use `pip install -e ".[dev]"` for development installation