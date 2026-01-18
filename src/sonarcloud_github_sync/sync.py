"""Core synchronization logic between SonarCloud and GitHub."""

import re
from typing import List, Optional
from .config import Config
from .sonar_client import SonarClient, SonarIssue
from .github_client import GitHubClient, GitHubIssue
from .logging_config import get_logger


class SyncEngine:
    """Handles synchronization between SonarCloud and GitHub."""
    
    def __init__(self, config: Config, dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.logger = get_logger(__name__)
        self.sonar_client = SonarClient(config.sonar_token)
        self.github_client = GitHubClient(config.github_token)
        
        self.logger.debug(f"SyncEngine initialized with dry_run={dry_run}")
        self.logger.debug(f"Config: project={config.sonar_project_key}, repo={config.github_repo}, types={config.issue_types}")
    
    def validate_credentials(self) -> bool:
        """Validate that credentials work for both services."""
        self.logger.debug("Validating SonarCloud credentials")
        if not self.sonar_client.test_connection():
            self.logger.error("SonarCloud credential validation failed")
            raise Exception("Invalid SonarCloud credentials or connection failed")
        
        self.logger.debug("Validating GitHub credentials and repository access")
        if not self.github_client.test_connection(self.config.github_repo):
            self.logger.error(f"GitHub credential validation failed for repo: {self.config.github_repo}")
            raise Exception("Invalid GitHub credentials or repository access failed")
        
        self.logger.info("All credentials validated successfully")
        return True
    
    def sync_sonar_to_github(self) -> dict:
        """Sync SonarCloud issues to GitHub."""
        self.logger.info(f"Starting SonarCloud to GitHub sync for project: {self.config.sonar_project_key}")
        self.logger.debug(f"Filtering by issue types: {self.config.issue_types}")
        
        self.logger.info(f"Fetching issues from SonarCloud project: {self.config.sonar_project_key}")
        sonar_issues = self.sonar_client.get_issues(
            self.config.sonar_project_key, 
            self.config.issue_types
        )
        
        self.logger.info(f"Retrieved {len(sonar_issues)} issues from SonarCloud")
        self.logger.debug(f"Issue keys: {[issue.key for issue in sonar_issues]}")
        self.logger.info(f"Found {len(sonar_issues)} issues in SonarCloud")
        
        created_count = 0
        skipped_count = 0
        closed_count = 0
        
        # Create GitHub issues for new SonarCloud issues
        self.logger.debug("Checking for existing GitHub issues and creating new ones")
        total_issues = len(sonar_issues)
        for idx, sonar_issue in enumerate(sonar_issues, start=1):
            self.logger.info(f"[{idx}/{total_issues}] Processing SonarCloud issue: {sonar_issue.key} - {sonar_issue.message[:50]}...")
            
            existing_github_issue = self.github_client.issue_exists_with_sonar_link(
                self.config.github_repo, 
                sonar_issue.url
            )
            
            if existing_github_issue:
                self.logger.debug(f"Found existing GitHub issue #{existing_github_issue.number} for SonarCloud issue {sonar_issue.key}")
                self.logger.info(f"[{idx}/{total_issues}] Skipping duplicate for SonarCloud issue {sonar_issue.key}")
                skipped_count += 1
                continue
            
            # Create GitHub issue
            github_title = sonar_issue.message
            github_body = self._create_github_issue_body(sonar_issue)
            github_labels = ["sonarcloud"] + sonar_issue.tags
            
            self.logger.debug(f"Preparing to create GitHub issue for {sonar_issue.key}")
            self.logger.debug(f"Title: {github_title}")
            self.logger.debug(f"Labels: {github_labels}")
            
            if self.dry_run:
                self.logger.info(f"[{idx}/{total_issues}] [DRY RUN] Would create GitHub issue for SonarCloud issue {sonar_issue.key}")
                self.logger.info(f"  Title: {github_title}")
                self.logger.info(f"  Labels: {', '.join(github_labels)}")
                created_count += 1
            else:
                try:
                    self.logger.debug(f"Making API call to create GitHub issue for {sonar_issue.key}")
                    github_issue = self.github_client.create_issue(
                        self.config.github_repo,
                        github_title,
                        github_body,
                        github_labels
                    )
                    self.logger.info(f"Successfully created GitHub issue #{github_issue.number} for SonarCloud issue {sonar_issue.key}")
                    self.logger.info(f"[{idx}/{total_issues}] Created GitHub issue #{github_issue.number} for SonarCloud issue {sonar_issue.key}")
                    created_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to create GitHub issue for {sonar_issue.key}: {e}")
                    self.logger.info(f"[{idx}/{total_issues}] Failed to create GitHub issue for {sonar_issue.key}: {e}")
        
        # Check for SonarCloud issues that are now resolved and close corresponding GitHub issues
        self.logger.debug("Checking for resolved SonarCloud issues to close corresponding GitHub issues")
        github_issues = self.github_client.get_issues_with_label(self.config.github_repo, "sonarcloud")
        self.logger.debug(f"Found {len(github_issues)} GitHub issues with 'sonarcloud' label")
        
        total_github_issues = len(github_issues)
        for idx, github_issue in enumerate(github_issues, start=1):
            if github_issue.state == "open":
                sonar_issue_key = self._extract_sonar_issue_key(github_issue.body)
                self.logger.info(f"[{idx}/{total_github_issues}] Processing open GitHub issue #{github_issue.number}, linked to SonarCloud issue: {sonar_issue_key}")

                if sonar_issue_key:
                    # Check if this SonarCloud issue still exists and is open
                    if not any(si.key == sonar_issue_key for si in sonar_issues):
                        self.logger.debug(f"SonarCloud issue {sonar_issue_key} no longer open, closing GitHub issue #{github_issue.number}")
                        if self.dry_run:
                            self.logger.info(f"[{idx}/{total_github_issues}] [DRY RUN] Would close GitHub issue #{github_issue.number} (SonarCloud issue {sonar_issue_key} resolved)")
                            closed_count += 1
                        else:
                            try:
                                self.logger.debug(f"Making API call to close GitHub issue #{github_issue.number}")
                                self.github_client.close_issue(self.config.github_repo, github_issue.number)
                                self.logger.info(f"Successfully closed GitHub issue #{github_issue.number} (SonarCloud issue {sonar_issue_key} resolved)")
                                self.logger.info(f"[{idx}/{total_github_issues}] Closed GitHub issue #{github_issue.number} (SonarCloud issue {sonar_issue_key} resolved)")
                                closed_count += 1
                            except Exception as e:
                                self.logger.error(f"Failed to close GitHub issue #{github_issue.number}: {e}")
                                self.logger.info(f"[{idx}/{total_github_issues}] Failed to close GitHub issue #{github_issue.number}: {e}")
                else:
                    self.logger.warning(f"Could not extract SonarCloud issue key from GitHub issue #{github_issue.number}")
        
        return {
            "created": created_count,
            "skipped": skipped_count,
            "closed": closed_count
        }
    
    def sync_github_to_sonar(self) -> dict:
        """Sync GitHub issue closures back to SonarCloud."""
        self.logger.info("Starting GitHub to SonarCloud sync")
        self.logger.info("Checking GitHub issues for SonarCloud sync")
        
        github_issues = self.github_client.get_issues_with_label(self.config.github_repo, "sonarcloud")
        self.logger.debug(f"Found {len(github_issues)} GitHub issues with 'sonarcloud' label for reverse sync")
        marked_wont_fix = 0
        
        total_github_issues = len(github_issues)
        for idx, github_issue in enumerate(github_issues, start=1):
            self.logger.debug(f"Processing GitHub issue #{github_issue.number}, state: {github_issue.state}, state_reason: {github_issue.state_reason}")
            
            if github_issue.state == "closed" and github_issue.state_reason == "not_planned":
                sonar_issue_key = self._extract_sonar_issue_key(github_issue.body)
                self.logger.debug(f"GitHub issue #{github_issue.number} closed as 'not_planned', linked to SonarCloud issue: {sonar_issue_key}")
                
                if sonar_issue_key:
                    if self.dry_run:
                        self.logger.info(f"[{idx}/{total_github_issues}] [DRY RUN] Would mark SonarCloud issue {sonar_issue_key} as 'Won't Fix'")
                        marked_wont_fix += 1
                    else:
                        try:
                            self.logger.debug(f"Making API call to mark SonarCloud issue {sonar_issue_key} as 'Won't Fix'")
                            success = self.sonar_client.resolve_issue_as_wont_fix(sonar_issue_key)
                            if success:
                                self.logger.info(f"Successfully marked SonarCloud issue {sonar_issue_key} as 'Won't Fix'")
                                self.logger.info(f"[{idx}/{total_github_issues}] Marked SonarCloud issue {sonar_issue_key} as 'Won't Fix'")
                                marked_wont_fix += 1
                        except Exception as e:
                            self.logger.error(f"Failed to mark SonarCloud issue {sonar_issue_key} as 'Won't Fix': {e}")
                            self.logger.info(f"[{idx}/{total_github_issues}] Failed to mark SonarCloud issue {sonar_issue_key} as 'Won't Fix': {e}")
                else:
                    self.logger.warning(f"Could not extract SonarCloud issue key from GitHub issue #{github_issue.number}")
            elif github_issue.state == "closed":
                self.logger.debug(f"GitHub issue #{github_issue.number} closed as '{github_issue.state_reason}', no action needed")
        
        return {
            "marked_wont_fix": marked_wont_fix
        }
    
    def full_sync(self) -> dict:
        """Perform full bidirectional sync."""
        self.logger.info(f"Starting full bidirectional sync (dry_run={self.dry_run})")
        
        if self.dry_run:
            self.logger.info("Starting full synchronization (DRY RUN MODE)...")
        else:
            self.logger.info("Starting full synchronization...")
        
        # Validate credentials first
        self.logger.debug("Validating credentials before sync")
        self.validate_credentials()
        self.logger.info("Credentials validated successfully")
        
        # Sync SonarCloud -> GitHub
        self.logger.debug("Starting SonarCloud to GitHub sync phase")
        sonar_to_github_results = self.sync_sonar_to_github()
        
        # Sync GitHub -> SonarCloud
        self.logger.debug("Starting GitHub to SonarCloud sync phase")
        github_to_sonar_results = self.sync_github_to_sonar()
        
        results = {
            **sonar_to_github_results,
            **github_to_sonar_results
        }
        
        self.logger.info(f"Sync completed with results: {results}")
        
        if self.dry_run:
            self.logger.info("Dry run completed successfully")
            self.logger.info("Synchronization preview completed (DRY RUN MODE)!")
            self.logger.info(f"Would create: {results['created']} GitHub issues")
            self.logger.info(f"Would skip: {results['skipped']} duplicates")
            self.logger.info(f"Would close: {results['closed']} GitHub issues")
            self.logger.info(f"Would mark as Won't Fix: {results['marked_wont_fix']} SonarCloud issues")
        else:
            self.logger.info("Full sync completed successfully")
            self.logger.info("Synchronization completed!")
            self.logger.info(f"Created: {results['created']} GitHub issues")
            self.logger.info(f"Skipped: {results['skipped']} duplicates")
            self.logger.info(f"Closed: {results['closed']} GitHub issues")
            self.logger.info(f"Marked as Won't Fix: {results['marked_wont_fix']} SonarCloud issues")
        
        return results
    
    def _create_github_issue_body(self, sonar_issue: SonarIssue) -> str:
        """Create the body text for a GitHub issue from a SonarCloud issue."""
        body_parts = [
            f"**SonarCloud Issue:** {sonar_issue.key}",
            f"**Type:** {sonar_issue.type}",
            f"**Severity:** {sonar_issue.severity}",
            f"**Component:** {sonar_issue.component}",
            "",
            f"**Description:**",
            sonar_issue.message,
            "",
            f"**SonarCloud Link:** {sonar_issue.url}",
            "",
            "---",
            "*This issue was automatically created from SonarCloud*"
        ]
        
        if sonar_issue.tags:
            body_parts.insert(-3, f"**Tags:** {', '.join(sonar_issue.tags)}")
            body_parts.insert(-3, "")
        
        return "\n".join(body_parts)
    
    def _extract_sonar_issue_key(self, github_body: str) -> Optional[str]:
        """Extract SonarCloud issue key from GitHub issue body."""
        match = re.search(r'\*\*SonarCloud Issue:\*\* ([A-Za-z0-9_:-]+)', github_body)
        return match.group(1) if match else None
