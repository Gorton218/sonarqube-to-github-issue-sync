"""Tests for configuration management."""

import os
import pytest
from unittest.mock import patch
from sonarcloud_github_sync.config import Config


class TestConfig:
    """Test configuration management."""
    
    def test_config_creation_with_all_fields(self):
        """Test creating config with all fields provided."""
        config = Config(
            sonar_token="test-sonar-token",
            github_token="test-github-token",
            sonar_project_key="test-project",
            github_repo="owner/repo",
            issue_types=["BUG", "VULNERABILITY"]
        )
        
        assert config.sonar_token == "test-sonar-token"
        assert config.github_token == "test-github-token"
        assert config.sonar_project_key == "test-project"
        assert config.github_repo == "owner/repo"
        assert config.issue_types == ["BUG", "VULNERABILITY"]
    
    def test_config_creation_with_defaults(self):
        """Test creating config with default issue types."""
        config = Config(
            sonar_token="test-sonar-token",
            github_token="test-github-token",
            sonar_project_key="test-project",
            github_repo="owner/repo"
        )
        
        assert config.issue_types == ["BUG", "VULNERABILITY", "CODE_SMELL"]
    
    @patch.dict(os.environ, {
        "SONAR_TOKEN": "env-sonar-token",
        "GITHUB_TOKEN": "env-github-token"
    })
    def test_from_env_success(self):
        """Test creating config from environment variables."""
        config = Config.from_env(
            sonar_project_key="test-project",
            github_repo="owner/repo"
        )
        
        assert config.sonar_token == "env-sonar-token"
        assert config.github_token == "env-github-token"
        assert config.sonar_project_key == "test-project"
        assert config.github_repo == "owner/repo"
        assert config.issue_types == ["BUG", "VULNERABILITY", "CODE_SMELL"]
    
    @patch.dict(os.environ, {
        "SONAR_TOKEN": "env-sonar-token",
        "GITHUB_TOKEN": "env-github-token"
    })
    def test_from_env_with_custom_issue_types(self):
        """Test creating config from env with custom issue types."""
        config = Config.from_env(
            sonar_project_key="test-project",
            github_repo="owner/repo",
            issue_types=["BUG"]
        )
        
        assert config.issue_types == ["BUG"]
    
    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_missing_sonar_token(self):
        """Test error when SONAR_TOKEN is missing."""
        with pytest.raises(ValueError, match="SONAR_TOKEN environment variable is required"):
            Config.from_env(
                sonar_project_key="test-project",
                github_repo="owner/repo"
            )
    
    @patch.dict(os.environ, {"SONAR_TOKEN": "test-token"}, clear=True)
    def test_from_env_missing_github_token(self):
        """Test error when GITHUB_TOKEN is missing."""
        with pytest.raises(ValueError, match="GITHUB_TOKEN environment variable is required"):
            Config.from_env(
                sonar_project_key="test-project",
                github_repo="owner/repo"
            )