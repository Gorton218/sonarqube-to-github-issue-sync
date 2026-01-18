"""Tests for GitHub API client."""

import pytest
import responses
from sonarcloud_github_sync.github_client import GitHubClient, GitHubIssue


class TestGitHubClient:
    """Test GitHub API client."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = GitHubClient("test-token")
    
    @responses.activate
    def test_get_issues_with_label_success(self):
        """Test successful issue retrieval with label."""
        # Mock API response
        responses.add(
            responses.GET,
            "https://api.github.com/repos/owner/repo/issues",
            json=[
                {
                    "number": 1,
                    "title": "Test Issue 1",
                    "body": "Test body 1",
                    "state": "open",
                    "labels": [{"name": "sonarcloud"}, {"name": "bug"}],
                    "state_reason": None
                },
                {
                    "number": 2,
                    "title": "Test Issue 2",
                    "body": "Test body 2",
                    "state": "closed",
                    "labels": [{"name": "sonarcloud"}],
                    "state_reason": "completed"
                }
            ],
            status=200
        )
        
        issues = self.client.get_issues_with_label("owner/repo", "sonarcloud")
        
        assert len(issues) == 2
        assert issues[0].number == 1
        assert issues[0].title == "Test Issue 1"
        assert issues[0].state == "open"
        assert issues[0].labels == ["sonarcloud", "bug"]
        assert issues[1].number == 2
        assert issues[1].state == "closed"
        assert issues[1].state_reason == "completed"
    
    @responses.activate
    def test_get_issues_with_label_pagination(self):
        """Test pagination handling."""
        # First page
        responses.add(
            responses.GET,
            "https://api.github.com/repos/owner/repo/issues",
            json=[{"number": i, "title": f"Issue {i}", "body": "", "state": "open", "labels": []}
                  for i in range(1, 101)],  # 100 issues
            status=200
        )
        
        # Second page (empty)
        responses.add(
            responses.GET,
            "https://api.github.com/repos/owner/repo/issues",
            json=[],
            status=200
        )
        
        issues = self.client.get_issues_with_label("owner/repo", "sonarcloud")
        
        assert len(issues) == 100
        assert len(responses.calls) == 2
    
    @responses.activate
    def test_get_issues_with_label_error(self):
        """Test error handling in issue retrieval."""
        responses.add(
            responses.GET,
            "https://api.github.com/repos/owner/repo/issues",
            status=404
        )
        
        with pytest.raises(Exception, match="Failed to fetch GitHub issues"):
            self.client.get_issues_with_label("owner/repo", "sonarcloud")
    
    @responses.activate
    def test_create_issue_success(self):
        """Test successful issue creation."""
        responses.add(
            responses.POST,
            "https://api.github.com/repos/owner/repo/issues",
            json={
                "number": 123,
                "title": "New Issue",
                "body": "Issue body",
                "state": "open",
                "labels": [{"name": "sonarcloud"}, {"name": "bug"}]
            },
            status=201
        )
        
        issue = self.client.create_issue(
            "owner/repo",
            "New Issue",
            "Issue body",
            ["sonarcloud", "bug"]
        )
        
        assert issue.number == 123
        assert issue.title == "New Issue"
        assert issue.labels == ["sonarcloud", "bug"]
        
        # Check request data
        assert len(responses.calls) == 1
        import json
        request_data = json.loads(responses.calls[0].request.body)
        assert request_data["title"] == "New Issue"
        assert request_data["body"] == "Issue body"
        assert request_data["labels"] == ["sonarcloud", "bug"]
    
    @responses.activate
    def test_create_issue_error(self):
        """Test error handling in issue creation."""
        responses.add(
            responses.POST,
            "https://api.github.com/repos/owner/repo/issues",
            status=422
        )
        
        with pytest.raises(Exception, match="Failed to create GitHub issue"):
            self.client.create_issue("owner/repo", "Title", "Body")
    
    @responses.activate
    def test_close_issue_success(self):
        """Test successful issue closure."""
        responses.add(
            responses.PATCH,
            "https://api.github.com/repos/owner/repo/issues/123",
            status=200
        )
        
        result = self.client.close_issue("owner/repo", 123)
        
        assert result is True
        # Check request data
        import json
        request_data = json.loads(responses.calls[0].request.body)
        assert request_data["state"] == "closed"
    
    @responses.activate
    def test_close_issue_error(self):
        """Test error handling in issue closure."""
        responses.add(
            responses.PATCH,
            "https://api.github.com/repos/owner/repo/issues/123",
            status=404
        )
        
        with pytest.raises(Exception, match="Failed to close GitHub issue"):
            self.client.close_issue("owner/repo", 123)
    
    @responses.activate
    def test_get_issue_events_success(self):
        """Test successful issue events retrieval."""
        responses.add(
            responses.GET,
            "https://api.github.com/repos/owner/repo/issues/123/events",
            json=[
                {"event": "closed", "actor": {"login": "user"}},
                {"event": "labeled", "label": {"name": "bug"}}
            ],
            status=200
        )
        
        events = self.client.get_issue_events("owner/repo", 123)
        
        assert len(events) == 2
        assert events[0]["event"] == "closed"
    
    @responses.activate
    def test_issue_exists_with_sonar_link_found(self):
        """Test finding existing issue with SonarCloud link."""
        responses.add(
            responses.GET,
            "https://api.github.com/repos/owner/repo/issues",
            json=[
                {
                    "number": 1,
                    "title": "Issue 1",
                    "body": "Contains https://sonarcloud.io/project/issues?id=test&issues=key1",
                    "state": "open",
                    "labels": [{"name": "sonarcloud"}]
                },
                {
                    "number": 2,
                    "title": "Issue 2", 
                    "body": "Different body",
                    "state": "open",
                    "labels": [{"name": "sonarcloud"}]
                }
            ],
            status=200
        )
        
        sonar_url = "https://sonarcloud.io/project/issues?id=test&issues=key1"
        issue = self.client.issue_exists_with_sonar_link("owner/repo", sonar_url)
        
        assert issue is not None
        assert issue.number == 1
    
    @responses.activate
    def test_issue_exists_with_sonar_link_not_found(self):
        """Test not finding issue with SonarCloud link."""
        responses.add(
            responses.GET,
            "https://api.github.com/repos/owner/repo/issues",
            json=[
                {
                    "number": 1,
                    "title": "Issue 1",
                    "body": "Different SonarCloud link",
                    "state": "open",
                    "labels": [{"name": "sonarcloud"}]
                }
            ],
            status=200
        )
        
        sonar_url = "https://sonarcloud.io/project/issues?id=test&issues=key2"
        issue = self.client.issue_exists_with_sonar_link("owner/repo", sonar_url)
        
        assert issue is None
    
    @responses.activate
    def test_test_connection_success(self):
        """Test successful connection validation."""
        responses.add(
            responses.GET,
            "https://api.github.com/repos/owner/repo",
            json={"name": "repo"},
            status=200
        )
        
        result = self.client.test_connection("owner/repo")
        assert result is True
    
    @responses.activate
    def test_test_connection_error(self):
        """Test connection error."""
        responses.add(
            responses.GET,
            "https://api.github.com/repos/owner/repo",
            status=404
        )
        
        result = self.client.test_connection("owner/repo")
        assert result is False


class TestGitHubIssue:
    """Test GitHubIssue model."""
    
    def test_github_issue_creation(self):
        """Test creating a GitHubIssue."""
        issue = GitHubIssue(
            number=123,
            title="Test Issue",
            body="Test body",
            state="open",
            labels=["bug", "enhancement"],
            state_reason="completed"
        )
        
        assert issue.number == 123
        assert issue.title == "Test Issue"
        assert issue.state == "open"
        assert issue.labels == ["bug", "enhancement"]
        assert issue.state_reason == "completed"
    
    def test_github_issue_creation_with_defaults(self):
        """Test creating GitHubIssue with default values."""
        issue = GitHubIssue(
            number=123,
            title="Test Issue",
            body="Test body",
            state="open"
        )
        
        assert issue.labels == []
        assert issue.state_reason is None