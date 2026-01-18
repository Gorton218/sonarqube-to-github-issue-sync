"""Tests for synchronization engine."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sonarcloud_github_sync.sync import SyncEngine
from sonarcloud_github_sync.config import Config
from sonarcloud_github_sync.sonar_client import SonarIssue
from sonarcloud_github_sync.github_client import GitHubIssue


class TestSyncEngine:
    """Test synchronization engine."""
    
    def setup_method(self):
        """Set up test sync engine."""
        self.config = Config(
            sonar_token="test-sonar-token",
            github_token="test-github-token",
            sonar_project_key="test-project",
            github_repo="owner/repo",
            issue_types=["BUG", "VULNERABILITY"]
        )
        self.sync_engine = SyncEngine(self.config)
    
    def test_init_with_dry_run(self):
        """Test initialization with dry run mode."""
        sync_engine = SyncEngine(self.config, dry_run=True)
        assert sync_engine.dry_run is True
    
    def test_init_without_dry_run(self):
        """Test initialization without dry run mode."""
        sync_engine = SyncEngine(self.config)
        assert sync_engine.dry_run is False
    
    @patch('sonarcloud_github_sync.sync.SonarClient')
    @patch('sonarcloud_github_sync.sync.GitHubClient')
    def test_validate_credentials_success(self, mock_github_client, mock_sonar_client):
        """Test successful credential validation."""
        # Mock client instances
        mock_sonar_instance = Mock()
        mock_github_instance = Mock()
        mock_sonar_client.return_value = mock_sonar_instance
        mock_github_client.return_value = mock_github_instance
        
        # Mock successful connections
        mock_sonar_instance.test_connection.return_value = True
        mock_github_instance.test_connection.return_value = True
        
        sync_engine = SyncEngine(self.config)
        result = sync_engine.validate_credentials()
        
        assert result is True
        mock_sonar_instance.test_connection.assert_called_once()
        mock_github_instance.test_connection.assert_called_once_with("owner/repo")
    
    @patch('sonarcloud_github_sync.sync.SonarClient')
    @patch('sonarcloud_github_sync.sync.GitHubClient')
    def test_validate_credentials_sonar_failure(self, mock_github_client, mock_sonar_client):
        """Test credential validation with SonarCloud failure."""
        mock_sonar_instance = Mock()
        mock_github_instance = Mock()
        mock_sonar_client.return_value = mock_sonar_instance
        mock_github_client.return_value = mock_github_instance
        
        mock_sonar_instance.test_connection.return_value = False
        
        sync_engine = SyncEngine(self.config)
        
        with pytest.raises(Exception, match="Invalid SonarCloud credentials"):
            sync_engine.validate_credentials()
    
    @patch('sonarcloud_github_sync.sync.SonarClient')
    @patch('sonarcloud_github_sync.sync.GitHubClient')
    def test_validate_credentials_github_failure(self, mock_github_client, mock_sonar_client):
        """Test credential validation with GitHub failure."""
        mock_sonar_instance = Mock()
        mock_github_instance = Mock()
        mock_sonar_client.return_value = mock_sonar_instance
        mock_github_client.return_value = mock_github_instance
        
        mock_sonar_instance.test_connection.return_value = True
        mock_github_instance.test_connection.return_value = False
        
        sync_engine = SyncEngine(self.config)
        
        with pytest.raises(Exception, match="Invalid GitHub credentials"):
            sync_engine.validate_credentials()
    
    @patch('sonarcloud_github_sync.sync.SonarClient')
    @patch('sonarcloud_github_sync.sync.GitHubClient')
    def test_sync_sonar_to_github_create_new_issues(self, mock_github_client, mock_sonar_client):
        """Test creating new GitHub issues from SonarCloud."""
        # Mock client instances
        mock_sonar_instance = Mock()
        mock_github_instance = Mock()
        mock_sonar_client.return_value = mock_sonar_instance
        mock_github_client.return_value = mock_github_instance
        
        # Mock SonarCloud issues
        sonar_issues = [
            SonarIssue(
                key="issue-1",
                type="BUG",
                severity="MAJOR",
                status="OPEN",
                message="Test bug",
                component="test-component",
                project="test-project",
                tags=["security"]
            ),
            SonarIssue(
                key="issue-2",
                type="VULNERABILITY",
                severity="CRITICAL",
                status="OPEN",
                message="Security issue",
                component="test-component",
                project="test-project",
                tags=[]
            )
        ]
        mock_sonar_instance.get_issues.return_value = sonar_issues
        
        # Mock GitHub - no existing issues
        mock_github_instance.issue_exists_with_sonar_link.return_value = None
        mock_github_instance.get_issues_with_label.return_value = []
        
        # Mock GitHub issue creation
        mock_github_instance.create_issue.side_effect = [
            GitHubIssue(number=1, title="Test bug", body="", state="open"),
            GitHubIssue(number=2, title="Security issue", body="", state="open")
        ]
        
        sync_engine = SyncEngine(self.config)
        results = sync_engine.sync_sonar_to_github()
        
        assert results["created"] == 2
        assert results["skipped"] == 0
        assert results["closed"] == 0
        assert mock_github_instance.create_issue.call_count == 2
    
    @patch('sonarcloud_github_sync.sync.SonarClient')
    @patch('sonarcloud_github_sync.sync.GitHubClient')
    def test_sync_sonar_to_github_skip_existing(self, mock_github_client, mock_sonar_client):
        """Test skipping existing GitHub issues."""
        mock_sonar_instance = Mock()
        mock_github_instance = Mock()
        mock_sonar_client.return_value = mock_sonar_instance
        mock_github_client.return_value = mock_github_instance
        
        # Mock SonarCloud issues
        sonar_issues = [
            SonarIssue(
                key="issue-1",
                type="BUG",
                severity="MAJOR",
                status="OPEN",
                message="Test bug",
                component="test-component",
                project="test-project"
            )
        ]
        mock_sonar_instance.get_issues.return_value = sonar_issues
        
        # Mock existing GitHub issue
        existing_issue = GitHubIssue(number=1, title="Test bug", body="", state="open")
        mock_github_instance.issue_exists_with_sonar_link.return_value = existing_issue
        mock_github_instance.get_issues_with_label.return_value = []
        
        sync_engine = SyncEngine(self.config)
        results = sync_engine.sync_sonar_to_github()
        
        assert results["created"] == 0
        assert results["skipped"] == 1
        assert results["closed"] == 0
        mock_github_instance.create_issue.assert_not_called()
    
    @patch('sonarcloud_github_sync.sync.SonarClient')
    @patch('sonarcloud_github_sync.sync.GitHubClient')
    def test_sync_sonar_to_github_dry_run(self, mock_github_client, mock_sonar_client):
        """Test dry run mode for SonarCloud to GitHub sync."""
        mock_sonar_instance = Mock()
        mock_github_instance = Mock()
        mock_sonar_client.return_value = mock_sonar_instance
        mock_github_client.return_value = mock_github_instance
        
        # Mock SonarCloud issues
        sonar_issues = [
            SonarIssue(
                key="issue-1",
                type="BUG",
                severity="MAJOR",
                status="OPEN",
                message="Test bug",
                component="test-component",
                project="test-project"
            )
        ]
        mock_sonar_instance.get_issues.return_value = sonar_issues
        mock_github_instance.issue_exists_with_sonar_link.return_value = None
        mock_github_instance.get_issues_with_label.return_value = []
        
        sync_engine = SyncEngine(self.config, dry_run=True)
        results = sync_engine.sync_sonar_to_github()
        
        assert results["created"] == 1
        assert results["skipped"] == 0
        # Should not actually create issues in dry run
        mock_github_instance.create_issue.assert_not_called()
    
    @patch('sonarcloud_github_sync.sync.SonarClient')
    @patch('sonarcloud_github_sync.sync.GitHubClient')
    def test_sync_github_to_sonar_mark_wont_fix(self, mock_github_client, mock_sonar_client):
        """Test marking SonarCloud issues as won't fix."""
        mock_sonar_instance = Mock()
        mock_github_instance = Mock()
        mock_sonar_client.return_value = mock_sonar_instance
        mock_github_client.return_value = mock_github_instance
        
        # Mock GitHub issues
        github_issues = [
            GitHubIssue(
                number=1,
                title="Test Issue",
                body="**SonarCloud Issue:** issue-1\nSome content",
                state="closed",
                labels=["sonarcloud"],
                state_reason="not_planned"
            ),
            GitHubIssue(
                number=2,
                title="Another Issue",
                body="**SonarCloud Issue:** issue-2\nSome content",
                state="closed",
                labels=["sonarcloud"],
                state_reason="completed"  # Should not trigger won't fix
            )
        ]
        mock_github_instance.get_issues_with_label.return_value = github_issues
        mock_sonar_instance.resolve_issue_as_wont_fix.return_value = True
        
        sync_engine = SyncEngine(self.config)
        results = sync_engine.sync_github_to_sonar()
        
        assert results["marked_wont_fix"] == 1
        mock_sonar_instance.resolve_issue_as_wont_fix.assert_called_once_with("issue-1")
    
    @patch('sonarcloud_github_sync.sync.SonarClient')
    @patch('sonarcloud_github_sync.sync.GitHubClient')
    def test_sync_github_to_sonar_dry_run(self, mock_github_client, mock_sonar_client):
        """Test dry run mode for GitHub to SonarCloud sync."""
        mock_sonar_instance = Mock()
        mock_github_instance = Mock()
        mock_sonar_client.return_value = mock_sonar_instance
        mock_github_client.return_value = mock_github_instance
        
        # Mock GitHub issues
        github_issues = [
            GitHubIssue(
                number=1,
                title="Test Issue",
                body="**SonarCloud Issue:** issue-1\nSome content",
                state="closed",
                labels=["sonarcloud"],
                state_reason="not_planned"
            )
        ]
        mock_github_instance.get_issues_with_label.return_value = github_issues
        
        sync_engine = SyncEngine(self.config, dry_run=True)
        results = sync_engine.sync_github_to_sonar()
        
        assert results["marked_wont_fix"] == 1
        # Should not actually mark issues in dry run
        mock_sonar_instance.resolve_issue_as_wont_fix.assert_not_called()
    
    def test_create_github_issue_body(self):
        """Test GitHub issue body creation."""
        sonar_issue = SonarIssue(
            key="test-key",
            type="BUG",
            severity="MAJOR",
            status="OPEN",
            message="Test message",
            component="test-component",
            project="test-project",
            tags=["security", "performance"]
        )
        
        sync_engine = SyncEngine(self.config)
        body = sync_engine._create_github_issue_body(sonar_issue)
        
        assert "**SonarCloud Issue:** test-key" in body
        assert "**Type:** BUG" in body
        assert "**Severity:** MAJOR" in body
        assert "**Component:** test-component" in body
        assert "**Description:**" in body
        assert "Test message" in body
        assert "**Tags:** security, performance" in body
        assert sonar_issue.url in body
        assert "*This issue was automatically created from SonarCloud*" in body
    
    def test_create_github_issue_body_no_tags(self):
        """Test GitHub issue body creation without tags."""
        sonar_issue = SonarIssue(
            key="test-key",
            type="BUG",
            severity="MAJOR",
            status="OPEN",
            message="Test message",
            component="test-component",
            project="test-project",
            tags=[]
        )
        
        sync_engine = SyncEngine(self.config)
        body = sync_engine._create_github_issue_body(sonar_issue)
        
        assert "**Tags:**" not in body
    
    def test_extract_sonar_issue_key_success(self):
        """Test extracting SonarCloud issue key from GitHub body."""
        body = """
        Some content
        **SonarCloud Issue:** test-issue-key-123
        More content
        """
        
        sync_engine = SyncEngine(self.config)
        key = sync_engine._extract_sonar_issue_key(body)
        
        assert key == "test-issue-key-123"
    
    def test_extract_sonar_issue_key_not_found(self):
        """Test extracting SonarCloud issue key when not found."""
        body = "Some content without SonarCloud issue key"
        
        sync_engine = SyncEngine(self.config)
        key = sync_engine._extract_sonar_issue_key(body)
        
        assert key is None
    
    @patch('sonarcloud_github_sync.sync.SonarClient')
    @patch('sonarcloud_github_sync.sync.GitHubClient')
    def test_full_sync_integration(self, mock_github_client, mock_sonar_client):
        """Test full sync integration."""
        mock_sonar_instance = Mock()
        mock_github_instance = Mock()
        mock_sonar_client.return_value = mock_sonar_instance
        mock_github_client.return_value = mock_github_instance
        
        # Mock credential validation
        mock_sonar_instance.test_connection.return_value = True
        mock_github_instance.test_connection.return_value = True
        
        # Mock SonarCloud sync
        mock_sonar_instance.get_issues.return_value = []
        mock_github_instance.get_issues_with_label.return_value = []
        mock_github_instance.issue_exists_with_sonar_link.return_value = None
        
        sync_engine = SyncEngine(self.config)
        
        with patch.object(sync_engine, 'sync_sonar_to_github') as mock_s2g:
            with patch.object(sync_engine, 'sync_github_to_sonar') as mock_g2s:
                mock_s2g.return_value = {"created": 1, "skipped": 0, "closed": 0}
                mock_g2s.return_value = {"marked_wont_fix": 1}
                
                results = sync_engine.full_sync()
                
                assert results["created"] == 1
                assert results["marked_wont_fix"] == 1
                mock_s2g.assert_called_once()
                mock_g2s.assert_called_once()