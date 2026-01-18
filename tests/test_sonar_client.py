"""Tests for SonarCloud API client."""

import pytest
import responses
from sonarcloud_github_sync.sonar_client import SonarClient, SonarIssue


class TestSonarClient:
    """Test SonarCloud API client."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = SonarClient("test-token")
    
    @responses.activate
    def test_get_issues_success(self):
        """Test successful issue retrieval."""
        # Mock API response
        responses.add(
            responses.GET,
            "https://sonarcloud.io/api/issues/search",
            json={
                "issues": [
                    {
                        "key": "test-issue-1",
                        "type": "BUG",
                        "severity": "MAJOR",
                        "status": "OPEN",
                        "message": "Test issue message",
                        "component": "test-component",
                        "project": "test-project",
                        "tags": ["test-tag"]
                    },
                    {
                        "key": "test-issue-2",
                        "type": "VULNERABILITY",
                        "severity": "CRITICAL",
                        "status": "OPEN",
                        "message": "Security issue",
                        "component": "test-component-2",
                        "project": "test-project",
                        "tags": []
                    }
                ]
            },
            status=200
        )
        
        issues = self.client.get_issues("test-project")
        
        assert len(issues) == 2
        assert issues[0].key == "test-issue-1"
        assert issues[0].type == "BUG"
        assert issues[0].severity == "MAJOR"
        assert issues[0].message == "Test issue message"
        assert issues[0].tags == ["test-tag"]
        assert issues[1].key == "test-issue-2"
        assert issues[1].type == "VULNERABILITY"
        assert issues[1].tags == []
    
    @responses.activate
    def test_get_issues_with_filter(self):
        """Test issue retrieval with type filter."""
        responses.add(
            responses.GET,
            "https://sonarcloud.io/api/issues/search",
            json={"issues": []},
            status=200
        )
        
        self.client.get_issues("test-project", ["BUG", "VULNERABILITY"])
        
        # Check that the request was made with correct parameters
        assert len(responses.calls) == 1
        request = responses.calls[0].request
        assert "types=BUG%2CVULNERABILITY" in request.url
    
    @responses.activate
    def test_get_issues_api_error(self):
        """Test handling of API errors."""
        responses.add(
            responses.GET,
            "https://sonarcloud.io/api/issues/search",
            status=401
        )
        
        with pytest.raises(Exception, match="Failed to fetch SonarCloud issues"):
            self.client.get_issues("test-project")
    
    @responses.activate
    def test_resolve_issue_as_wont_fix_success(self):
        """Test successful issue resolution."""
        responses.add(
            responses.POST,
            "https://sonarcloud.io/api/issues/do_transition",
            status=200
        )
        
        result = self.client.resolve_issue_as_wont_fix("test-issue-key")
        
        assert result is True
        # Check request data
        assert len(responses.calls) == 1
        request = responses.calls[0].request
        assert "issue=test-issue-key" in request.body
        assert "transition=wontfix" in request.body
    
    @responses.activate
    def test_resolve_issue_as_wont_fix_error(self):
        """Test error handling in issue resolution."""
        responses.add(
            responses.POST,
            "https://sonarcloud.io/api/issues/do_transition",
            status=404
        )
        
        with pytest.raises(Exception, match="Failed to resolve SonarCloud issue"):
            self.client.resolve_issue_as_wont_fix("test-issue-key")
    
    @responses.activate
    def test_test_connection_success(self):
        """Test successful connection validation."""
        responses.add(
            responses.GET,
            "https://sonarcloud.io/api/authentication/validate",
            json={"valid": True},
            status=200
        )
        
        result = self.client.test_connection()
        assert result is True
    
    @responses.activate
    def test_test_connection_invalid(self):
        """Test invalid connection."""
        responses.add(
            responses.GET,
            "https://sonarcloud.io/api/authentication/validate",
            json={"valid": False},
            status=200
        )
        
        result = self.client.test_connection()
        assert result is False
    
    @responses.activate
    def test_test_connection_error(self):
        """Test connection error."""
        responses.add(
            responses.GET,
            "https://sonarcloud.io/api/authentication/validate",
            status=500
        )
        
        result = self.client.test_connection()
        assert result is False


class TestSonarIssue:
    """Test SonarIssue model."""
    
    def test_sonar_issue_creation(self):
        """Test creating a SonarIssue."""
        issue = SonarIssue(
            key="test-key",
            type="BUG",
            severity="MAJOR",
            status="OPEN",
            message="Test message",
            component="test-component",
            project="test-project",
            tags=["tag1", "tag2"]
        )
        
        assert issue.key == "test-key"
        assert issue.type == "BUG"
        assert issue.tags == ["tag1", "tag2"]
    
    def test_sonar_issue_url_generation(self):
        """Test URL generation for SonarIssue."""
        issue = SonarIssue(
            key="test-key",
            type="BUG",
            severity="MAJOR",
            status="OPEN",
            message="Test message",
            component="test-component",
            project="test-project"
        )
        
        expected_url = "https://sonarcloud.io/project/issues?id=test-project&issues=test-key&open=test-key"
        assert issue.url == expected_url