## **Tasks**

* \[ \] 1.0 **Setup Basic CLI Structure and Configuration**  
  * \[ \] 1.1 Initialize a new Python project.  
  * \[ \] 1.2 Add a command-line argument parsing library (e.g., yargs) to handle potential future flags.  
  * \[ \] 1.3 Implement logic to read SONAR\_TOKEN and GITHUB\_TOKEN from environment variables.  
  * \[ \] 1.4 Add a configuration flag (e.g., \--issue-types=BUG,VULNERABILITY) to support filtering issues by type.  
* \[ \] 2.0 **Implement API Clients for GitHub and SonarCloud**  
  * \[ \] 2.1 Create a module for the GitHub API client with functions to: fetch issues by label, create a new issue, and close an issue.  
  * \[ \] 2.2 Create a module for the SonarCloud API client with functions to: fetch issues for a project and transition an issue's state to "Won't Fix".  
  * \[ \] 2.3 Write basic unit tests for both API clients, mocking the network requests to verify function calls.  
* \[ \] 3.0 **Develop Core Synchronization Logic (SonarCloud to GitHub)**  
  * \[ \] 3.1 Fetch all open issues from the specified SonarCloud project using the API client.  
  * \[ \] 3.2 Filter the fetched SonarCloud issues based on the issue type configuration from step 1.4.  
  * \[ \] 3.3 For each SonarCloud issue, implement a function to search existing GitHub issues for a unique identifier (the SonarCloud issue link in the body) to prevent duplicates.  
  * \[ \] 3.4 If no duplicate is found, call the GitHub client to create a new issue with the mapped title, body, and labels.  
  * \[ \] 3.5 Implement logic to query for GitHub issues with the sonarcloud label that correspond to issues that are now *closed* in SonarCloud, and close them on GitHub.  
* \[ \] 4.0 **Implement Reverse Sync Logic (GitHub to SonarCloud)**  
  * \[ \] 4.1 Fetch all GitHub issues with the sonarcloud label.  
  * \[ \] 4.2 For each issue, check if its state is "closed".  
  * \[ \] 4.3 If the issue is closed, query the GitHub API for its close reason.  
  * \[ \] 4.4 If the close reason is "Not Planned", extract the SonarCloud issue URL from the GitHub issue body and call the SonarCloud client to resolve the issue as "Won't Fix".  
* \[ \] 5.0 **Finalize with Error Handling, Logging, and Documentation**  
  * \[ \] 5.1 Add robust error handling for API failures (e.g., network errors, rate limits, invalid tokens) throughout the application.  
  * \[ \] 5.2 Implement clear console logging to show the tool's progress (e.g., "Found 15 issues in SonarCloud", "Creating new issue for SC-123", "Skipping duplicate...", "Marking SC-456 as Won't Fix").  
  * \[ \] 5.3 Write a comprehensive README.md file detailing installation, setup (how to set environment variables), and all command-line options.  
  * \[ \] 5.4 Expand unit tests to cover the core synchronization logic in sync.ts, including edge cases like duplicate detection and state transitions.