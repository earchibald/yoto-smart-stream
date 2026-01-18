#!/usr/bin/env python3
"""
Helper script to determine the appropriate CDK environment name based on the current git branch.

Branch-specific deployment workflow:
- copilot/* branches (PR sessions) -> Use branch-specific environment with PR ID
- copilot-* branches (VS Code background sessions) -> Use branch-specific environment
- aws-develop branch -> Use 'dev' environment
- aws-main branch -> Use 'prod' environment
- Other branches -> Use 'dev' environment (default)

The environment name is used to create isolated CDK stacks and AWS resources.
"""
import os
import re
import subprocess
import sys
from typing import Optional


def get_current_branch() -> str:
    """Get the current git branch name."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting current branch: {e}", file=sys.stderr)
        sys.exit(1)


def get_pr_number() -> Optional[str]:
    """
    Try to get the PR number from environment variables.

    GitHub Actions sets GITHUB_REF for pull requests as: refs/pull/:prNumber/merge
    Copilot environments may also provide PR_NUMBER or PULL_REQUEST_NUMBER.

    Returns:
        PR number as string, or None if not in a PR context
    """
    # Try environment variables that Copilot or GitHub Actions might set
    pr_number = os.getenv("PR_NUMBER") or os.getenv("PULL_REQUEST_NUMBER")
    if pr_number:
        return pr_number

    # Try to extract from GITHUB_REF
    github_ref = os.getenv("GITHUB_REF", "")
    if github_ref.startswith("refs/pull/"):
        # Extract PR number from refs/pull/123/merge
        match = re.match(r"refs/pull/(\d+)/", github_ref)
        if match:
            return match.group(1)

    # Try to get from git branch description or remote tracking
    try:
        # Check if the branch has a PR number in its description
        result = subprocess.run(
            ["git", "config", f"branch.{get_current_branch()}.description"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            desc = result.stdout.strip()
            # Look for PR number in description (e.g., "PR #123" or "#123")
            match = re.search(r"#(\d+)", desc)
            if match:
                return match.group(1)
    except Exception:
        pass

    return None


def normalize_environment_name(branch_name: str, pr_number: Optional[str] = None) -> str:
    """
    Normalize a branch name to a valid CDK environment name.

    Rules:
    - Replace '/' with '-'
    - Convert to lowercase
    - Remove or replace invalid characters
    - Ensure it starts with a letter
    - Limit length to reasonable size (63 chars max for DNS)
    - Include PR number if provided (for better isolation)

    Args:
        branch_name: Git branch name
        pr_number: Optional PR number to include in the name

    Returns:
        Normalized environment name suitable for CDK
    """
    # Replace slashes with hyphens
    env_name = branch_name.replace("/", "-")

    # Convert to lowercase
    env_name = env_name.lower()

    # Replace underscores with hyphens
    env_name = env_name.replace("_", "-")

    # Remove any characters that aren't alphanumeric or hyphens
    env_name = re.sub(r"[^a-z0-9-]", "", env_name)

    # Remove consecutive hyphens
    env_name = re.sub(r"-+", "-", env_name)

    # Remove leading/trailing hyphens
    env_name = env_name.strip("-")

    # Append PR number if provided (for better isolation and identification)
    if pr_number:
        env_name = f"{env_name}-pr{pr_number}"

    # Ensure it starts with a letter (prepend 'e-' if it doesn't)
    if not env_name or not env_name[0].isalpha():
        env_name = f"e-{env_name}"

    # Limit length to 50 characters (leaves room for resource suffixes)
    if len(env_name) > 50:
        env_name = env_name[:50].rstrip("-")

    return env_name


def get_deployment_environment(branch_name: Optional[str] = None) -> str:
    """
    Determine the appropriate CDK environment name for deployment.

    Args:
        branch_name: Optional branch name (defaults to current branch)

    Returns:
        CDK environment name to use for deployment
    """
    if branch_name is None:
        branch_name = get_current_branch()

    # Handle special branches
    if branch_name == "aws-main":
        return "prod"
    elif branch_name == "aws-develop":
        return "dev"

    # Get PR number for copilot branches
    pr_number = None
    if branch_name.startswith("copilot/"):
        # For copilot/* branches (PR sessions), include PR number if available
        pr_number = get_pr_number()

    # Copilot PR branches (copilot/*)
    if branch_name.startswith("copilot/"):
        return normalize_environment_name(branch_name, pr_number)
    # Copilot VS Code background agent branches (copilot-*)
    elif branch_name.startswith("copilot-"):
        return normalize_environment_name(branch_name)
    # Default to dev for all other branches
    else:
        return "dev"


def main():
    """Main entry point - prints the environment name to stdout."""
    branch = get_current_branch()
    pr_number = get_pr_number()
    env = get_deployment_environment(branch)
    print(env)

    # Optional: Print info to stderr for debugging
    if "--verbose" in sys.argv or "-v" in sys.argv:
        print(f"Branch: {branch}", file=sys.stderr)
        print(f"PR Number: {pr_number or 'N/A'}", file=sys.stderr)
        print(f"Environment: {env}", file=sys.stderr)


if __name__ == "__main__":
    main()
