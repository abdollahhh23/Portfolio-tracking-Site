#!/usr/bin/env python3
import datetime
import os
import subprocess
import sys


def create_historical_commit(target_date_str: str, commit_count: int = 1):
    """Creates a specific number of commits on a target historical date.

    Args:
        target_date_str (str): Date string in 'YYYY-MM-DD' format.
        commit_count (int): Number of commits to generate for that day.
    """
    # 1. Validate the input date format
    try:
        target_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d")
    except ValueError:
        print("Error: Date must be in YYYY-MM-DD format.")
        sys.exit(1)

    # 2. Check if the current directory is a initialized Git repository
    if not os.path.exists(".git"):
        print("Error: This directory is not a Git repository. Run 'git init' first.")
        sys.exit(1)

    filename = "activity_log.txt"

    for i in range(1, commit_count + 1):
        # Generate varied times (e.g., 10:15 AM, 2:30 PM) to look natural
        hour = 10 if i == 1 else 14
        minute = 15 * i
        timestamp = target_date.replace(
            hour=hour, minute=minute, second=0
        ).isoformat()

        # Isolate environmental variables for Git
        git_env = os.environ.copy()
        git_env["GIT_AUTHOR_DATE"] = timestamp
        git_env["GIT_COMMITTER_DATE"] = timestamp

        # Make a minor change to a tracking file
        with open(filename, "a") as f:
            f.write(f"Log entry for {target_date_str} - Sequence point {i}\n")

        try:
            # Stage the tracking file change
            subprocess.run(["git", "add", filename], check=True)

            # Execute the commit with the isolated timestamp environment
            commit_message = f"Update activity log for {target_date_str} [part {i}]"
            subprocess.run(
                ["git", "commit", "-m", commit_message], env=git_env, check=True
            )

            print(f"Successfully created commit {i} for timestamp: {timestamp}")

        except subprocess.CalledProcessError as e:
            print(f"Subprocess execution failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    # Example Target Context
    input_date = "2025-5-22"
    number_of_commits = 2

    create_historical_commit(input_date, commit_count=number_of_commits)