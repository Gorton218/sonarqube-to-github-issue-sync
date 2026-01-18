"""Tests for CLI interface."""

import pytest
from unittest.mock import patch, Mock
from click.testing import CliRunner
from sonarcloud_github_sync.cli import main


class TestCLI:
    """Test CLI interface."""
    
    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner(env={'LC_ALL': 'C.UTF-8', 'LANG': 'C.UTF-8'})
    
    def test_cli_help(self):
        """Test CLI help message."""
        result = self.runner.invoke(main, ['--help'])
        assert result.exit_code == 0
        assert "Synchronize issues between SonarCloud and GitHub" in result.output
        assert "--sonar-project" in result.output
        assert "--github-repo" in result.output
        assert "--issue-types" in result.output
        assert "--dry-run" in result.output
    
    def test_cli_missing_required_args(self):
        """Test CLI with missing required arguments."""
        result = self.runner.invoke(main, [])
        assert result.exit_code == 2
        assert "Missing option" in result.output
    
    @patch.dict('os.environ', {
        'SONAR_TOKEN': 'test-sonar-token',
        'GITHUB_TOKEN': 'test-github-token'
    })
    @patch('sonarcloud_github_sync.cli.SyncEngine')
    def test_cli_successful_sync(self, mock_sync_engine):
        """Test successful CLI execution."""
        # Mock sync engine
        mock_instance = Mock()
        mock_sync_engine.return_value = mock_instance
        mock_instance.full_sync.return_value = {
            'created': 5,
            'skipped': 2,
            'closed': 1,
            'marked_wont_fix': 0
        }
        
        result = self.runner.invoke(main, [
            '--sonar-project', 'test-project',
            '--github-repo', 'owner/repo'
        ])
        
        assert result.exit_code == 0
        assert "SYNC COMPLETED SUCCESSFULLY" in result.output
        assert "GitHub issues created: 5" in result.output
        assert "Duplicates skipped: 2" in result.output
        assert "GitHub issues closed: 1" in result.output
        assert "SonarCloud issues marked as 'Won't Fix': 0" in result.output
        
        # Verify sync engine was called correctly
        mock_sync_engine.assert_called_once()
        args, kwargs = mock_sync_engine.call_args
        config = args[0]
        assert config.sonar_project_key == 'test-project'
        assert config.github_repo == 'owner/repo'
        assert config.issue_types == ['BUG', 'VULNERABILITY', 'CODE_SMELL']
        assert kwargs['dry_run'] is False
    
    @patch.dict('os.environ', {
        'SONAR_TOKEN': 'test-sonar-token',
        'GITHUB_TOKEN': 'test-github-token'
    })
    @patch('sonarcloud_github_sync.cli.SyncEngine')
    def test_cli_with_custom_issue_types(self, mock_sync_engine):
        """Test CLI with custom issue types."""
        mock_instance = Mock()
        mock_sync_engine.return_value = mock_instance
        mock_instance.full_sync.return_value = {
            'created': 0, 'skipped': 0, 'closed': 0, 'marked_wont_fix': 0
        }
        
        result = self.runner.invoke(main, [
            '--sonar-project', 'test-project',
            '--github-repo', 'owner/repo',
            '--issue-types', 'BUG,VULNERABILITY'
        ])
        
        assert result.exit_code == 0
        
        # Verify custom issue types were parsed
        args, kwargs = mock_sync_engine.call_args
        config = args[0]
        assert config.issue_types == ['BUG', 'VULNERABILITY']
    
    @patch.dict('os.environ', {
        'SONAR_TOKEN': 'test-sonar-token',
        'GITHUB_TOKEN': 'test-github-token'
    })
    @patch('sonarcloud_github_sync.cli.SyncEngine')
    def test_cli_dry_run(self, mock_sync_engine):
        """Test CLI dry run mode."""
        mock_instance = Mock()
        mock_sync_engine.return_value = mock_instance
        mock_instance.full_sync.return_value = {
            'created': 3, 'skipped': 1, 'closed': 0, 'marked_wont_fix': 1
        }
        
        result = self.runner.invoke(main, [
            '--sonar-project', 'test-project',
            '--github-repo', 'owner/repo',
            '--dry-run'
        ])
        
        assert result.exit_code == 0
        # In dry run mode, should not show the success banner
        assert "SYNC COMPLETED SUCCESSFULLY" not in result.output
        
        # Verify dry run was enabled
        args, kwargs = mock_sync_engine.call_args
        assert kwargs['dry_run'] is True
    
    def test_cli_missing_sonar_token(self):
        """Test CLI with missing SONAR_TOKEN."""
        with patch.dict('os.environ', {'GITHUB_TOKEN': 'test-token'}, clear=True):
            result = self.runner.invoke(main, [
                '--sonar-project', 'test-project',
                '--github-repo', 'owner/repo'
            ])
            
            assert result.exit_code == 1
            assert "Configuration Error" in result.output
            assert "SONAR_TOKEN environment variable is required" in result.output
    
    def test_cli_missing_github_token(self):
        """Test CLI with missing GITHUB_TOKEN."""
        with patch.dict('os.environ', {'SONAR_TOKEN': 'test-token'}, clear=True):
            result = self.runner.invoke(main, [
                '--sonar-project', 'test-project',
                '--github-repo', 'owner/repo'
            ])
            
            assert result.exit_code == 1
            assert "Configuration Error" in result.output
            assert "GITHUB_TOKEN environment variable is required" in result.output
    
    @patch.dict('os.environ', {
        'SONAR_TOKEN': 'test-sonar-token',
        'GITHUB_TOKEN': 'test-github-token'
    })
    @patch('sonarcloud_github_sync.cli.SyncEngine')
    def test_cli_sync_error(self, mock_sync_engine):
        """Test CLI handling of sync errors."""
        mock_instance = Mock()
        mock_sync_engine.return_value = mock_instance
        mock_instance.full_sync.side_effect = Exception("Sync failed")
        
        result = self.runner.invoke(main, [
            '--sonar-project', 'test-project',
            '--github-repo', 'owner/repo'
        ])
        
        assert result.exit_code == 1
        assert "Sync Error: Sync failed" in result.output
    
    def test_cli_issue_type_parsing(self):
        """Test issue type parsing with different formats."""
        with patch.dict('os.environ', {
            'SONAR_TOKEN': 'test-token',
            'GITHUB_TOKEN': 'test-token'
        }):
            with patch('sonarcloud_github_sync.cli.SyncEngine') as mock_sync_engine:
                mock_instance = Mock()
                mock_sync_engine.return_value = mock_instance
                mock_instance.full_sync.return_value = {
                    'created': 0, 'skipped': 0, 'closed': 0, 'marked_wont_fix': 0
                }
                
                # Test with spaces
                result = self.runner.invoke(main, [
                    '--sonar-project', 'test-project',
                    '--github-repo', 'owner/repo',
                    '--issue-types', ' BUG , VULNERABILITY , CODE_SMELL '
                ])
                
                assert result.exit_code == 0
                args, kwargs = mock_sync_engine.call_args
                config = args[0]
                assert config.issue_types == ['BUG', 'VULNERABILITY', 'CODE_SMELL']