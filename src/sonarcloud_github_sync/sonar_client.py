"""SonarCloud API client."""

from typing import List, Dict, Any
import requests
from pydantic import BaseModel
from .logging_config import get_logger


class SonarIssue(BaseModel):
    """Represents a SonarCloud issue."""
    
    key: str
    type: str
    severity: str
    status: str
    message: str
    component: str
    project: str
    tags: List[str] = []
    
    @property
    def url(self) -> str:
        """Generate the SonarCloud issue URL."""
        return f"https://sonarcloud.io/project/issues?id={self.project}&issues={self.key}&open={self.key}"


class SonarClient:
    """Client for interacting with SonarCloud API."""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://sonarcloud.io/api"
        self.logger = get_logger(__name__)
        self.session = requests.Session()
        self.session.auth = (token, "")
        
        self.logger.debug("SonarCloud client initialized")
    
    def get_issues(self, project_key: str, issue_types: List[str] = None) -> List[SonarIssue]:
        """Fetch issues from SonarCloud project."""
        self.logger.debug(f"Fetching SonarCloud issues for project {project_key} with types {issue_types}")
        url = f"{self.base_url}/issues/search"
        params = {
            "componentKeys": project_key,
            "statuses": "OPEN",
            "ps": 500  # Page size
        }
        
        if issue_types:
            params["types"] = ",".join(issue_types)
            self.logger.debug(f"Filtering by issue types: {issue_types}")
        
        try:
            self.logger.debug(f"Making API request to SonarCloud: {url}")
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            issues = []
            for issue_data in data.get("issues", []):
                issue = SonarIssue(
                    key=issue_data["key"],
                    type=issue_data["type"],
                    severity=issue_data["severity"],
                    status=issue_data["status"],
                    message=issue_data["message"],
                    component=issue_data["component"],
                    project=issue_data["project"],
                    tags=issue_data.get("tags", [])
                )
                issues.append(issue)
            
            self.logger.debug(f"Retrieved {len(issues)} SonarCloud issues")
            return issues
            
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch SonarCloud issues for project {project_key}: {e}")
            raise Exception(f"Failed to fetch SonarCloud issues: {e}")
    
    def resolve_issue_as_wont_fix(self, issue_key: str) -> bool:
        """Mark a SonarCloud issue as 'Won't Fix'."""
        self.logger.debug(f"Marking SonarCloud issue {issue_key} as 'Won't Fix'")
        url = f"{self.base_url}/issues/do_transition"
        data = {
            "issue": issue_key,
            "transition": "wontfix"
        }
        
        try:
            response = self.session.post(url, data=data)
            response.raise_for_status()
            self.logger.debug(f"Successfully marked SonarCloud issue {issue_key} as 'Won't Fix'")
            return True
        except requests.RequestException as e:
            self.logger.error(f"Failed to resolve SonarCloud issue {issue_key}: {e}")
            raise Exception(f"Failed to resolve SonarCloud issue {issue_key}: {e}")
    
    def test_connection(self) -> bool:
        """Test if the SonarCloud connection is working."""
        self.logger.debug("Testing SonarCloud connection")
        url = f"{self.base_url}/authentication/validate"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            is_valid = data.get("valid", False)
            if is_valid:
                self.logger.debug("SonarCloud connection test successful")
            else:
                self.logger.debug("SonarCloud connection test failed: invalid credentials")
            return is_valid
        except requests.RequestException as e:
            self.logger.debug(f"SonarCloud connection test failed: {e}")
            return False