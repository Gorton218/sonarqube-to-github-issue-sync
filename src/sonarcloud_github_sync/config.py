"""Configuration management for the sync tool."""

import os
from typing import List, Optional
from pydantic import BaseModel, ValidationError


class Config(BaseModel):
    """Configuration for the SonarCloud-GitHub sync tool."""
    
    sonar_token: str
    github_token: str
    sonar_project_key: str
    github_repo: str
    issue_types: List[str] = ["BUG", "VULNERABILITY", "CODE_SMELL"]
    
    @classmethod
    def from_env(cls, sonar_project_key: str, github_repo: str, issue_types: Optional[List[str]] = None) -> "Config":
        """Create config from environment variables."""
        sonar_token = os.getenv("SONAR_TOKEN")
        github_token = os.getenv("GITHUB_TOKEN")
        
        if not sonar_token:
            raise ValueError("SONAR_TOKEN environment variable is required")
        if not github_token:
            raise ValueError("GITHUB_TOKEN environment variable is required")
            
        return cls(
            sonar_token=sonar_token,
            github_token=github_token,
            sonar_project_key=sonar_project_key,
            github_repo=github_repo,
            issue_types=issue_types or ["BUG", "VULNERABILITY", "CODE_SMELL"]
        )