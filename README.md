# GitLab Repository Archiver

The script `archive_repo.py` is used to archive a single repository, and `archive_multiple_repos.py` is used to archive multiple repositories at the same time by interacting with the GitLab API.

The scripts retrieve the repository's project ID, check the user's role to ensure they are an Owner or Maintainer, and then archive the repository. (Org Dependent)

# Features

- Retrieves the project ID of the entered GitLab repository.
- Retrieves the user's roles in the repository to check access levels.
- Provides detailed error messages for failed operations.
- No personal access token is needed however a user must be a ```Developer``` in order to successfully run the job (Org Dependent)

# Requirements

- The following environment variables must be set:
    - `USER_EMAIL`: The email address linked with your GitLab account.

- Be at least a ```Developer``` in the given repository that you are trying to archive (Org Dependent)

# Usage

To use this script, add the repository's SSH or HTTPS link into a Jenkins job

Enter a single link into the first box or add multiple links to the second. A combination of both will result in an error

Ensure there is only one link per line and click **Build**

