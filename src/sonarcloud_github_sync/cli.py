"""Command-line interface for the SonarCloud-GitHub sync tool."""

import sys
from typing import List, Optional
import click
from .config import Config
from .sync import SyncEngine
from .logging_config import setup_logging, get_logger


@click.command()
@click.option(
    "--sonar-project", 
    required=True, 
    help="SonarCloud project key (e.g., 'my-org_my-project')"
)
@click.option(
    "--github-repo", 
    required=True, 
    help="GitHub repository in format 'owner/repo' (e.g., 'myorg/myrepo')"
)
@click.option(
    "--issue-types", 
    default="BUG,VULNERABILITY,CODE_SMELL",
    help="Comma-separated list of issue types to sync (default: BUG,VULNERABILITY,CODE_SMELL)"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without making any changes"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging with detailed output"
)
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], case_sensitive=False),
    help="Set the logging level (default: INFO)"
)
@click.version_option()
def main(sonar_project: str, github_repo: str, issue_types: str, dry_run: bool, debug: bool, log_level: str):
    """Synchronize issues between SonarCloud and GitHub.
    
    This tool creates GitHub issues for SonarCloud issues and maintains
    bidirectional sync of issue states.
    
    Required environment variables:
    - SONAR_TOKEN: SonarCloud personal access token
    - GITHUB_TOKEN: GitHub personal access token
    
    Examples:
    
        # Basic sync
        sonarcloud-github-sync --sonar-project my-org_my-project --github-repo myorg/myrepo
        
        # Sync only bugs and vulnerabilities
        sonarcloud-github-sync --sonar-project my-org_my-project --github-repo myorg/myrepo --issue-types BUG,VULNERABILITY
        
        # Dry run to see what would happen
        sonarcloud-github-sync --sonar-project my-org_my-project --github-repo myorg/myrepo --dry-run
    """
    
    try:
        # Setup logging
        logger = setup_logging(level=log_level, debug=debug)
        logger.info("Starting SonarCloud-GitHub sync tool")
        logger.debug(f"CLI arguments: sonar_project={sonar_project}, github_repo={github_repo}, issue_types={issue_types}, dry_run={dry_run}, debug={debug}, log_level={log_level}")
        
        # Parse issue types
        issue_type_list = [t.strip().upper() for t in issue_types.split(",")]
        logger.debug(f"Parsed issue types: {issue_type_list}")
        
        # Create configuration
        config = Config.from_env(
            sonar_project_key=sonar_project,
            github_repo=github_repo,
            issue_types=issue_type_list
        )
        logger.debug(f"Configuration created: project={config.sonar_project_key}, repo={config.github_repo}, types={config.issue_types}")
        
        # Create sync engine and run
        logger.info("Initializing sync engine")
        sync_engine = SyncEngine(config, dry_run=dry_run)
        results = sync_engine.full_sync()
        
        # Report results
        logger.info("Sync operation completed")
        if not dry_run:
            click.echo("\n" + "="*50)
            click.echo("SYNC COMPLETED SUCCESSFULLY")
            click.echo("="*50)
            click.echo(f"GitHub issues created: {results['created']}")
            click.echo(f"Duplicates skipped: {results['skipped']}")  
            click.echo(f"GitHub issues closed: {results['closed']}")
            click.echo(f"SonarCloud issues marked as 'Won't Fix': {results['marked_wont_fix']}")
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        click.echo(f"Configuration Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Sync error: {e}", exc_info=debug)
        click.echo(f"Sync Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()