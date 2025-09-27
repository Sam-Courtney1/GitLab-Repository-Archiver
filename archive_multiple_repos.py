import requests
import os
import boto3
import sys

def get_api_token():
    param_name = "/tools-jenkins/gitlab-api-token"
    region_name = "us-east-1"

    client = boto3.client("ssm", region_name=region_name)

    try:
        return client.get_parameter(
            Name=param_name,
            WithDecryption=True
        )['Parameter']['Value']
    except Exception as e:
        print(f"ERROR: Could not retrieve GitLab token from SSM: {e}")
        sys.exit(1)

# Base access level for configured role. Valid values are 10 (Guest), 15 (Planner), 20 (Reporter), 30 (Developer), 40 (Maintainer), or 50 (Owner).

ACCESS_TOKEN = get_api_token()

GITLAB_URL = 'https://gitlab.com'

# Retrieves the project ID for the entered repo
def get_project_id(repo_path):
    headers = {'Private-Token': ACCESS_TOKEN }

    # URL-encode the repo path to allow api to retrieve information
    url = f'{GITLAB_URL}/api/v4/projects/{repo_path.replace("/", "%2F")}' 
    response = requests.get(url, headers=headers)
    
    # If the response is ok ie 200 , then return the project ID
    # If not then print error message and return none
    if response.status_code == 200:
        return response.json().get('id')
    else:
        print(f'Failed to retrieve project ID: {response.status_code} - {response.text}')
        return None

# Second function to get the role of a user
def get_user_role(project_id):
    headers = {'Private-Token': ACCESS_TOKEN }

    url = f'{GITLAB_URL}/api/v4/projects/{project_id}/members/all'
    roles = {}
    page = 1

    while True:
        params = {'page': page, 'per_page': 100}
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            members = response.json()
            if not members:
                break
            for member in members:
                roles[member['username']] = member['access_level']
            page += 1
        else:
            print(f'Failed to retrieve project members: {response.status_code} - {response.text}')
            return None

    return roles

# Function to resolve GitLab username
def resolve_gitlab_username(user_email, gitlab_usernames):
    """
    Resolves the GitLab username from the Jenkins USER_EMAIL.
    Tries deterministic matching first, then falls back to splitting the email prefix.
    """
    # Step 1: Replace '@' with '_' for primary matching
    derived_username = user_email.replace('@', '_')
    if derived_username in gitlab_usernames:
        return derived_username

    # Step 2: Split the email prefix into first and last name
    email_prefix = user_email.split('@')[0]  # Extract the part before '@'
    if '.' in email_prefix:
        first_name, last_name = email_prefix.split('.', 1)  # Split into first and last name
    else:
        print(f"\n\033[91mFailed to split email prefix: {email_prefix}\033[0m")
        raise Exception("Email prefix does not contain a dot for splitting.")

    # Step 3: Filter GitLab usernames that contain the first name
    potential_matches = [username for username in gitlab_usernames if first_name in username]

    # Step 4: Further filter to find usernames that also contain the last name
    final_matches = [username for username in potential_matches if last_name in username]

    # Step 5: Resolve matches
    if len(final_matches) == 1:
        return final_matches[0]  # Return the single match
    elif len(final_matches) > 1:
        print(f"Multiple potential matches found for {user_email}: {final_matches}")
        raise Exception("Ambiguous GitLab username. Please resolve manually.")
    else:
        print(f"No matching GitLab username found for {user_email}")
        raise Exception("GitLab username could not be resolved.")

if __name__ == '__main__':

    # Allows multiple lines to be read in with a single execution of the file
    with open('repos.txt', 'r') as file:  # Update this to take in multiple arguments from Jenkins
        for repo_path in file:
            # Remove any trailing whitespace or newline characters
            repo_path = repo_path.strip() 
            if not repo_path:
                continue

            print("The URL being searched is: ", repo_path)

            # Ensures consistency in the repo path
            if "://" in repo_path:
                repo_path = repo_path.split(".com/")[1].removesuffix(".git")
            else:
                repo_path = repo_path.split(".com:")[1].removesuffix(".git")
                
            # Passes the repo path to get the ID for a specific repo
            project_id = get_project_id(repo_path)
            print("The project ID is: ", project_id)

            if project_id:
                roles = get_user_role(project_id)
                """
                Get the username from the environment variable
                This ensures the username and the access token match
                """
                try:
                    gitlab_usernames = list(roles.keys())  # Get all GitLab usernames for the project
                    glab_username = resolve_gitlab_username(os.environ['USER_EMAIL'], gitlab_usernames)
                    permisson_value = roles[glab_username]
                    if roles and glab_username in roles:  # Checks if roles is not empty and if the user is in the roles
                        print(f"Username: {glab_username}, Access Level: {permisson_value}")

                        if permisson_value >= 30:
                            print("\033[92mUser has required access to archive\033[0m")
                            archive_url = f'{GITLAB_URL}/api/v4/projects/{project_id}/archive'
                            headers = {'Private-Token': ACCESS_TOKEN}

                            try:
                                response = requests.post(archive_url, headers=headers)
                                if response.status_code == 201:
                                    print("\033[92mThe repo has been archived successfully\033[0m")
                                    print(f"Project ID: {project_id}")
                                else:
                                    print(f'\033[91mFailed to archive project: {response.status_code} - {response.text}\033[0m')
                                    raise Exception

                            except requests.exceptions.RequestException as e:
                                print(f'\033[91mFailed to archive project: {e}\033[0m')
                                raise Exception
                        elif permisson_value < 30:  # Redundant check as if not 40 will always be less than 31
                            print("\033[91mUser does not have the required access to archive\033[0m")
                            raise Exception
                    else:
                        print(f"The user: {glab_username} was not found")
                        raise Exception
                except Exception as e:
                    print(f"\033[91mError: {e}\033[0m")
                    raise Exception
            else:
                print("Failed to retrieve project information.")
                raise Exception
        file.close()
