"""Integration tests for the sync tool."""

import pytest
from unittest.mock import patch, Mock
from sonarcloud_github_sync.config import Config
from sonarcloud_github_sync.sync import SyncEngine
from sonarcloud_github_sync.sonar_client import SonarIssue
from sonarcloud_github_sync.github_client import GitHubIssue


class TestIntegration:
    """Integration tests for sync functionality."""
    
    def setup_method(self):
        """Set up test configuration."""
        self.config = Config(
            sonar_token="test-sonar-token",
            github_token="test-github-token",
            sonar_project_key="test-project",
            github_repo="owner/repo",
            issue_types=["BUG", "VULNERABILITY"]
        )
    
    @patch('sonarcloud_github_sync.sync.SonarClient')
    @patch('sonarcloud_github_sync.sync.GitHubClient')
    def test_full_workflow_new_issues(self, mock_github_client, mock_sonar_client):
        """Test complete workflow with new issues."""
        # Setup mocks
        mock_sonar_instance = Mock()
        mock_github_instance = Mock()
        mock_sonar_client.return_value = mock_sonar_instance
        mock_github_client.return_value = mock_github_instance
        
        # Mock credential validation
        mock_sonar_instance.test_connection.return_value = True
        mock_github_instance.test_connection.return_value = True
        
        # Mock SonarCloud issues
        sonar_issues = [
            SonarIssue(
                key="sonar-1",
                type="BUG",
                severity="MAJOR",
                status="OPEN",
                message="Critical bug found",
                component="src/main.py",
                project="test-project",
                tags=["critical", "backend"]
            ),
            SonarIssue(
                key="sonar-2",
                type="VULNERABILITY",
                severity="HIGH",
                status="OPEN",
                message="Security vulnerability",
                component="src/auth.py",
                project="test-project",
                tags=["security"]
            )
        ]
        mock_sonar_instance.get_issues.return_value = sonar_issues
        
        # Mock GitHub - no existing issues
        mock_github_instance.issue_exists_with_sonar_link.return_value = None
        mock_github_instance.get_issues_with_label.return_value = []
        
        # Mock GitHub issue creation
        created_issues = [
            GitHubIssue(number=1, title="Critical bug found", body="", state="open"),
            GitHubIssue(number=2, title="Security vulnerability", body="", state="open")
        ]
        mock_github_instance.create_issue.side_effect = created_issues
        
        # Run sync
        sync_engine = SyncEngine(self.config)
        results = sync_engine.full_sync()
        
        # Verify results
        assert results["created"] == 2
        assert results["skipped"] == 0
        assert results["closed"] == 0
        assert results["marked_wont_fix"] == 0
        
        # Verify calls
        mock_sonar_instance.get_issues.assert_called_once_with("test-project", ["BUG", "VULNERABILITY"])
        assert mock_github_instance.create_issue.call_count == 2
        
        # Verify issue creation details
        create_calls = mock_github_instance.create_issue.call_args_list
        
        # First issue
        args1 = create_calls[0][0]
        assert args1[0] == "owner/repo"  # repo
        assert args1[1] == "Critical bug found"  # title
        assert "**SonarCloud Issue:** sonar-1" in args1[2]  # body contains issue key
        assert args1[3] == ["sonarcloud", "critical", "backend"]  # labels
        
        # Second issue
        args2 = create_calls[1][0]
        assert args2[1] == "Security vulnerability"
        assert "**SonarCloud Issue:** sonar-2" in args2[2]
        assert args2[3] == ["sonarcloud", "security"]
    
    @patch('sonarcloud_github_sync.sync.SonarClient')
    @patch('sonarcloud_github_sync.sync.GitHubClient')
    def test_full_workflow_with_duplicates_and_closures(self, mock_github_client, mock_sonar_client):
        """Test workflow with duplicate prevention and issue closures."""
        # Setup mocks
        mock_sonar_instance = Mock()
        mock_github_instance = Mock()
        mock_sonar_client.return_value = mock_sonar_instance
        mock_github_client.return_value = mock_github_instance
        
        # Mock credential validation
        mock_sonar_instance.test_connection.return_value = True
        mock_github_instance.test_connection.return_value = True
        
        # Mock SonarCloud - only one open issue now
        sonar_issues = [
            SonarIssue(
                key="sonar-1",
                type="BUG",
                severity="MAJOR",
                status="OPEN",
                message="Still active bug",
                component="src/main.py",
                project="test-project"
            )
        ]
        mock_sonar_instance.get_issues.return_value = sonar_issues
        
        # Mock GitHub - existing issues (some should be closed, one is duplicate)
        existing_github_issues = [
            GitHubIssue(
                number=1,
                title="Still active bug",
                body="**SonarCloud Issue:** sonar-1\nBody content\nhttps://sonarcloud.io/project/issues?id=test-project&issues=sonar-1",
                state="open",
                labels=["sonarcloud"]
            ),
            GitHubIssue(
                number=2,
                title="Resolved bug",
                body="**SonarCloud Issue:** sonar-2\nBody content",
                state="open",
                labels=["sonarcloud"]
            ),
            GitHubIssue(
                number=3,
                title="Won't fix issue",
                body="**SonarCloud Issue:** sonar-3\nBody content",
                state="closed",
                labels=["sonarcloud"],
                state_reason="not_planned"
            )
        ]
        
        def mock_issue_exists(repo, sonar_url):
            if "sonar-1" in sonar_url:
                return existing_github_issues[0]  # Duplicate found
            return None
        
        mock_github_instance.issue_exists_with_sonar_link.side_effect = mock_issue_exists
        mock_github_instance.get_issues_with_label.return_value = existing_github_issues
        mock_github_instance.close_issue.return_value = True
        mock_sonar_instance.resolve_issue_as_wont_fix.return_value = True
        
        # Run sync
        sync_engine = SyncEngine(self.config)
        results = sync_engine.full_sync()
        
        # Verify results
        assert results["created"] == 0  # No new issues created
        assert results["skipped"] == 1  # One duplicate skipped
        assert results["closed"] == 1  # One GitHub issue closed (sonar-2 resolved)
        assert results["marked_wont_fix"] == 1  # One SonarCloud issue marked won't fix
        
        # Verify GitHub issue closure
        mock_github_instance.close_issue.assert_called_once_with("owner/repo", 2)
        
        # Verify SonarCloud won't fix marking
        mock_sonar_instance.resolve_issue_as_wont_fix.assert_called_once_with("sonar-3")
    
    @patch('sonarcloud_github_sync.sync.SonarClient')
    @patch('sonarcloud_github_sync.sync.GitHubClient')
    def test_error_handling_during_sync(self, mock_github_client, mock_sonar_client):
        """Test error handling during synchronization."""
        # Setup mocks
        mock_sonar_instance = Mock()
        mock_github_instance = Mock()
        mock_sonar_client.return_value = mock_sonar_instance
        mock_github_client.return_value = mock_github_instance
        
        # Mock credential validation
        mock_sonar_instance.test_connection.return_value = True
        mock_github_instance.test_connection.return_value = True
        
        # Mock SonarCloud issues
        sonar_issues = [
            SonarIssue(
                key="sonar-1",
                type="BUG",
                severity="MAJOR",
                status="OPEN",
                message="Test bug",
                component="src/main.py",
                project="test-project"
            )
        ]
        mock_sonar_instance.get_issues.return_value = sonar_issues
        
        # Mock GitHub - no existing issues
        mock_github_instance.issue_exists_with_sonar_link.return_value = None
        mock_github_instance.get_issues_with_label.return_value = []
        
        # Mock GitHub issue creation failure
        mock_github_instance.create_issue.side_effect = Exception("GitHub API error")
        
        # Run sync - should not raise exception but handle error gracefully
        sync_engine = SyncEngine(self.config)
        results = sync_engine.full_sync()
        
        # Should complete with 0 created issues due to error
        assert results["created"] == 0
        assert results["skipped"] == 0
        assert results["closed"] == 0
        assert results["marked_wont_fix"] == 0
    
    @patch('sonarcloud_github_sync.sync.SonarClient')
    @patch('sonarcloud_github_sync.sync.GitHubClient')
    def test_dry_run_integration(self, mock_github_client, mock_sonar_client):
        """Test dry run mode integration."""
        # Setup mocks
        mock_sonar_instance = Mock()
        mock_github_instance = Mock()
        mock_sonar_client.return_value = mock_sonar_instance
        mock_github_client.return_value = mock_github_instance
        
        # Mock credential validation
        mock_sonar_instance.test_connection.return_value = True
        mock_github_instance.test_connection.return_value = True
        
        # Mock SonarCloud issues
        sonar_issues = [
            SonarIssue(
                key="sonar-1",
                type="BUG",
                severity="MAJOR",
                status="OPEN",
                message="Test bug",
                component="src/main.py",
                project="test-project"
            )
        ]
        mock_sonar_instance.get_issues.return_value = sonar_issues
        
        # Mock GitHub - existing closed issue that would trigger won't fix
        github_issues = [
            GitHubIssue(
                number=1,
                title="Test Issue",
                body="**SonarCloud Issue:** sonar-2\nContent",
                state="closed",
                labels=["sonarcloud"],
                state_reason="not_planned"
            )
        ]
        mock_github_instance.issue_exists_with_sonar_link.return_value = None
        mock_github_instance.get_issues_with_label.return_value = github_issues
        
        # Run dry run sync
        sync_engine = SyncEngine(self.config, dry_run=True)
        results = sync_engine.full_sync()
        
        # Verify results show what would happen
        assert results["created"] == 1
        assert results["marked_wont_fix"] == 1
        
        # Verify no actual API calls were made for modifications
        mock_github_instance.create_issue.assert_not_called()
        mock_github_instance.close_issue.assert_not_called()
        mock_sonar_instance.resolve_issue_as_wont_fix.assert_not_called()
    
    def test_issue_body_format_and_parsing(self):
        """Test issue body formatting and key extraction."""
        sync_engine = SyncEngine(self.config)
        
        # Create test SonarIssue
        sonar_issue = SonarIssue(
            key="complex-key_123:branch",
            type="VULNERABILITY",
            severity="HIGH",
            status="OPEN",
            message="SQL injection vulnerability found",
            component="src/database/query.py",
            project="my-org_my-project",
            tags=["security", "sql", "critical"]
        )
        
        # Generate GitHub issue body
        body = sync_engine._create_github_issue_body(sonar_issue)
        
        # Verify body contains all expected elements
        assert "**SonarCloud Issue:** complex-key_123:branch" in body
        assert "**Type:** VULNERABILITY" in body
        assert "**Severity:** HIGH" in body
        assert "**Component:** src/database/query.py" in body
        assert "SQL injection vulnerability found" in body
        assert "**Tags:** security, sql, critical" in body
        assert sonar_issue.url in body
        assert "*This issue was automatically created from SonarCloud*" in body
        
        # Test key extraction
        extracted_key = sync_engine._extract_sonar_issue_key(body)
        assert extracted_key == "complex-key_123:branch"
        
        # Test with edge cases
        edge_body = "**SonarCloud Issue:** key-with-underscores_and:colons-123"
        extracted_edge_key = sync_engine._extract_sonar_issue_key(edge_body)
        assert extracted_edge_key == "key-with-underscores_and:colons-123"