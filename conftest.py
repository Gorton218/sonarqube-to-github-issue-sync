"""Pytest configuration and shared fixtures."""

import pytest
from unittest.mock import Mock
from sonarcloud_github_sync.config import Config
from sonarcloud_github_sync.sonar_client import SonarIssue
from sonarcloud_github_sync.github_client import GitHubIssue


@pytest.fixture
def sample_config():
    """Provide a sample configuration for tests."""
    return Config(
        sonar_token="test-sonar-token",
        github_token="test-github-token",
        sonar_project_key="test-project",
        github_repo="owner/repo",
        issue_types=["BUG", "VULNERABILITY", "CODE_SMELL"]
    )


@pytest.fixture
def sample_sonar_issue():
    """Provide a sample SonarCloud issue for tests."""
    return SonarIssue(
        key="test-issue-1",
        type="BUG",
        severity="MAJOR",
        status="OPEN",
        message="Test issue message",
        component="src/test.py",
        project="test-project",
        tags=["test", "example"]
    )


@pytest.fixture
def sample_github_issue():
    """Provide a sample GitHub issue for tests."""
    return GitHubIssue(
        number=123,
        title="Test GitHub Issue",
        body="**SonarCloud Issue:** test-issue-1\nTest body content",
        state="open",
        labels=["sonarcloud", "bug"],
        state_reason=None
    )


@pytest.fixture
def mock_sonar_client():
    """Provide a mock SonarCloud client."""
    mock = Mock()
    mock.test_connection.return_value = True
    mock.get_issues.return_value = []
    mock.resolve_issue_as_wont_fix.return_value = True
    return mock


@pytest.fixture
def mock_github_client():
    """Provide a mock GitHub client."""
    mock = Mock()
    mock.test_connection.return_value = True
    mock.get_issues_with_label.return_value = []
    mock.issue_exists_with_sonar_link.return_value = None
    mock.create_issue.return_value = GitHubIssue(
        number=1, title="Test", body="", state="open"
    )
    mock.close_issue.return_value = True
    mock.get_issue_events.return_value = []
    return mock