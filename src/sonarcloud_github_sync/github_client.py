"""GitHub API client."""

from typing import List, Dict, Any, Optional
import requests
from pydantic import BaseModel
from .logging_config import get_logger


class GitHubIssue(BaseModel):
    """Represents a GitHub issue."""
    
    number: int
    title: str
    body: str
    state: str
    labels: List[str] = []
    state_reason: Optional[str] = None


class GitHubClient:
    """Client for interacting with GitHub API."""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.github.com"
        self.logger = get_logger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SonarCloud-GitHub-Sync/1.0"
        })
        
        self.logger.debug("GitHub client initialized")
    
    def get_issues_with_label(self, repo: str, label: str = "sonarcloud") -> List[GitHubIssue]:
        """Fetch GitHub issues with a specific label."""
        self.logger.debug(f"Fetching GitHub issues for repo {repo} with label '{label}'")
        url = f"{self.base_url}/repos/{repo}/issues"
        params = {
            "labels": label,
            "state": "all",
            "per_page": 100
        }
        
        try:
            issues = []
            page = 1
            
            while True:
                params["page"] = page
                self.logger.debug(f"Fetching page {page} of GitHub issues")
                response = self.session.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if not data:
                    break
                
                for issue_data in data:
                    issue = GitHubIssue(
                        number=issue_data["number"],
                        title=issue_data["title"],
                        body=issue_data.get("body", ""),
                        state=issue_data["state"],
                        labels=[label["name"] for label in issue_data.get("labels", [])],
                        state_reason=issue_data.get("state_reason")
                    )
                    issues.append(issue)
                
                if len(data) < 100:
                    break
                page += 1
            
            self.logger.debug(f"Retrieved {len(issues)} GitHub issues with label '{label}'")
            return issues
            
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch GitHub issues for repo {repo}: {e}")
            raise Exception(f"Failed to fetch GitHub issues: {e}")
    
    def create_issue(self, repo: str, title: str, body: str, labels: List[str] = None) -> GitHubIssue:
        """Create a new GitHub issue."""
        self.logger.debug(f"Creating GitHub issue in repo {repo}: {title[:50]}...")
        url = f"{self.base_url}/repos/{repo}/issues"
        data = {
            "title": title,
            "body": body,
            "labels": labels or []
        }
        self.logger.debug(f"Issue data: title={title}, labels={labels}")
        
        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            issue_data = response.json()
            
            created_issue = GitHubIssue(
                number=issue_data["number"],
                title=issue_data["title"],
                body=issue_data.get("body", ""),
                state=issue_data["state"],
                labels=[label["name"] for label in issue_data.get("labels", [])]
            )
            self.logger.debug(f"Successfully created GitHub issue #{created_issue.number}")
            return created_issue
            
        except requests.RequestException as e:
            self.logger.error(f"Failed to create GitHub issue in repo {repo}: {e}")
            raise Exception(f"Failed to create GitHub issue: {e}")
    
    def close_issue(self, repo: str, issue_number: int) -> bool:
        """Close a GitHub issue."""
        self.logger.debug(f"Closing GitHub issue #{issue_number} in repo {repo}")
        url = f"{self.base_url}/repos/{repo}/issues/{issue_number}"
        data = {"state": "closed"}
        
        try:
            response = self.session.patch(url, json=data)
            response.raise_for_status()
            self.logger.debug(f"Successfully closed GitHub issue #{issue_number}")
            return True
        except requests.RequestException as e:
            self.logger.error(f"Failed to close GitHub issue #{issue_number} in repo {repo}: {e}")
            raise Exception(f"Failed to close GitHub issue #{issue_number}: {e}")
    
    def get_issue_events(self, repo: str, issue_number: int) -> List[Dict[str, Any]]:
        """Get events for a GitHub issue to determine close reason."""
        url = f"{self.base_url}/repos/{repo}/issues/{issue_number}/events"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Failed to get events for GitHub issue #{issue_number}: {e}")
    
    def issue_exists_with_sonar_link(self, repo: str, sonar_issue_url: str) -> Optional[GitHubIssue]:
        """Check if a GitHub issue already exists for a SonarCloud issue."""
        issues = self.get_issues_with_label(repo, "sonarcloud")
        for issue in issues:
            if sonar_issue_url in issue.body:
                return issue
        return None
    
    def test_connection(self, repo: str) -> bool:
        """Test if the GitHub connection is working."""
        self.logger.debug(f"Testing GitHub connection for repo {repo}")
        url = f"{self.base_url}/repos/{repo}"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            self.logger.debug(f"GitHub connection test successful for repo {repo}")
            return True
        except requests.RequestException as e:
            self.logger.debug(f"GitHub connection test failed for repo {repo}: {e}")
            return False