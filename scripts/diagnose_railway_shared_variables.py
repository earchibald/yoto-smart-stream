#!/usr/bin/env python3
"""
Diagnostic script to investigate Railway shared variables issue.

This script comprehensively checks why ${{shared.YOTO_SERVER_CLIENT_ID}} might be
coming through as an empty string in PR environments.
"""

import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional


def run_command(cmd: List[str], capture=True) -> tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def check_railway_cli() -> bool:
    """Check if Railway CLI is installed and authenticated."""
    print("=" * 80)
    print("1. Checking Railway CLI Installation")
    print("=" * 80)
    
    # Check if railway CLI is installed
    code, stdout, stderr = run_command(["which", "railway"])
    if code != 0:
        print("❌ Railway CLI not found")
        print("   Install with: npm i -g @railway/cli")
        return False
    
    print(f"✅ Railway CLI found at: {stdout.strip()}")
    
    # Check version
    code, stdout, stderr = run_command(["railway", "version"])
    if code == 0:
        print(f"   Version: {stdout.strip()}")
    
    # Check if authenticated
    code, stdout, stderr = run_command(["railway", "whoami"])
    if code != 0:
        print("❌ Not authenticated with Railway")
        print("   Set RAILWAY_TOKEN environment variable")
        return False
    
    print(f"✅ Authenticated as: {stdout.strip()}")
    return True


def list_projects() -> Optional[str]:
    """List Railway projects and return project ID."""
    print("\n" + "=" * 80)
    print("2. Listing Railway Projects")
    print("=" * 80)
    
    code, stdout, stderr = run_command(["railway", "list", "--json"])
    if code != 0:
        print(f"❌ Failed to list projects: {stderr}")
        return None
    
    try:
        projects = json.loads(stdout) if stdout else []
        print(f"Found {len(projects)} project(s)")
        
        for project in projects:
            print(f"\n  Project: {project.get('name', 'Unknown')}")
            print(f"  ID: {project.get('id', 'Unknown')}")
        
        # Return first project ID if available
        if projects:
            return projects[0].get('id')
    except json.JSONDecodeError:
        print(f"❌ Failed to parse projects JSON")
    
    return None


def list_environments(project_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all environments in the Railway project."""
    print("\n" + "=" * 80)
    print("3. Listing Railway Environments")
    print("=" * 80)
    
    # Try to list environments
    code, stdout, stderr = run_command(["railway", "environment"])
    if code != 0:
        print(f"⚠️  Could not list environments: {stderr}")
        return []
    
    print(stdout)
    
    # Parse environment list
    environments = []
    for line in stdout.split('\n'):
        line = line.strip()
        if line and not line.startswith('->') and line:
            # Extract environment name from line
            parts = line.split()
            if parts:
                env_name = parts[0].replace('*', '').strip()
                if env_name and env_name not in ['NAME', 'Environment', '─']:
                    environments.append({'name': env_name})
    
    print(f"\nFound {len(environments)} environment(s)")
    return environments


def check_variable_in_environment(env_name: str, var_name: str = "YOTO_SERVER_CLIENT_ID") -> Optional[str]:
    """Check if a variable exists in a specific environment."""
    print(f"\n  Checking {var_name} in '{env_name}':")
    
    # Get all variables for this environment
    code, stdout, stderr = run_command(["railway", "variables", "-e", env_name])
    if code != 0:
        print(f"    ❌ Failed to get variables: {stderr}")
        return None
    
    # Parse variables
    lines = stdout.split('\n')
    for line in lines:
        if var_name in line:
            # Extract value
            parts = line.split('=', 1)
            if len(parts) == 2:
                value = parts[1].strip()
                if value:
                    masked = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
                    print(f"    ✅ Found: {var_name}={masked}")
                    print(f"       Length: {len(value)} characters")
                    return value
                else:
                    print(f"    ⚠️  Found but EMPTY: {var_name}=")
                    return ""
    
    print(f"    ❌ Not found: {var_name}")
    return None


def check_shared_variables() -> Dict[str, Any]:
    """Check shared variables configuration in Railway."""
    print("\n" + "=" * 80)
    print("4. Checking Shared Variables")
    print("=" * 80)
    
    print("\n⚠️  Note: Railway CLI doesn't have a direct command to list shared variables.")
    print("You need to check the Railway web UI at: https://railway.app")
    print("\nShared variables are configured in:")
    print("  Project Settings → Shared Variables")
    
    print("\n📋 What to check in Railway Web UI:")
    print("  1. Go to your project dashboard")
    print("  2. Click 'Settings' → 'Shared Variables'")
    print("  3. Verify YOTO_SERVER_CLIENT_ID is listed")
    print("  4. Check which environments it's shared WITH")
    print("  5. Verify the 'Source Environment' (should be 'production')")
    
    return {}


def check_variable_references() -> None:
    """Check how shared variables should be referenced."""
    print("\n" + "=" * 80)
    print("5. Variable Reference Syntax Analysis")
    print("=" * 80)
    
    print("\n📚 Railway Shared Variables Documentation:")
    print("  Reference: https://docs.railway.app/guides/variables#shared-variables")
    
    print("\n✅ CORRECT syntax for shared variables:")
    print("  ${{shared.VARIABLE_NAME}}")
    print("  Example: ${{shared.YOTO_SERVER_CLIENT_ID}}")
    
    print("\n❌ INCORRECT syntax:")
    print("  ${{production.YOTO_SERVER_CLIENT_ID}}  # Wrong - references environment, not shared")
    print("  ${YOTO_SERVER_CLIENT_ID}                # Wrong - shell syntax")
    print("  $YOTO_SERVER_CLIENT_ID                  # Wrong - direct reference")
    
    print("\n🔍 Common Issues:")
    print("  1. Typo in variable name (case-sensitive)")
    print("  2. Variable not marked as 'shared' in source environment")
    print("  3. Target environment not added to shared variable's scope")
    print("  4. Variable set in Railway UI but not marked for sharing")
    print("  5. Timing issue - variable hasn't propagated yet")


def check_pr_environment_setup() -> None:
    """Check PR environment configuration."""
    print("\n" + "=" * 80)
    print("6. PR Environment Configuration Analysis")
    print("=" * 80)
    
    print("\n📋 How Railway PR Environments inherit variables:")
    print("  1. PR environments inherit from a BASE environment (usually 'staging')")
    print("  2. Shared variables must be:")
    print("     a) Defined in source environment (e.g., 'production')")
    print("     b) Marked as SHARED in Railway UI")
    print("     c) Configured to be shared WITH target environments")
    print("  3. PR environments need explicit access to shared variables")
    
    print("\n⚠️  CRITICAL: Shared variables propagation")
    print("  - Shared variables are NOT automatically available to PR environments")
    print("  - You must explicitly configure sharing scope in Railway UI")
    print("  - Check: Settings → Shared Variables → Click on YOTO_SERVER_CLIENT_ID")
    print("  - Verify: 'Shared with' includes PR environments or 'All environments'")


def provide_troubleshooting_steps() -> None:
    """Provide step-by-step troubleshooting guide."""
    print("\n" + "=" * 80)
    print("7. Troubleshooting Steps")
    print("=" * 80)
    
    print("\n🔧 Step-by-step fix for empty shared variables:")
    
    print("\n  STEP 1: Verify in Railway Web UI")
    print("  ─────────────────────────────────")
    print("  1. Go to: https://railway.app")
    print("  2. Select your project: yoto-smart-stream")
    print("  3. Click: Settings (left sidebar)")
    print("  4. Click: Shared Variables")
    print("  5. Find: YOTO_SERVER_CLIENT_ID")
    print("     - If NOT listed: Variable is not shared! See STEP 2")
    print("     - If listed: Check 'Shared with' column")
    
    print("\n  STEP 2: Create/Fix Shared Variable")
    print("  ───────────────────────────────────")
    print("  1. In Railway dashboard, go to 'production' environment")
    print("  2. Click 'Variables' tab")
    print("  3. Find YOTO_SERVER_CLIENT_ID variable")
    print("  4. Click the ⋮ (three dots) menu next to it")
    print("  5. Select 'Share variable'")
    print("  6. Choose sharing scope:")
    print("     - Option A: 'All environments' (simplest)")
    print("     - Option B: Select specific environments (pr-*, staging, etc.)")
    print("  7. Save changes")
    
    print("\n  STEP 3: Verify Sharing Configuration")
    print("  ────────────────────────────────────")
    print("  1. Go back to: Settings → Shared Variables")
    print("  2. Click on 'YOTO_SERVER_CLIENT_ID' row")
    print("  3. Verify:")
    print("     - Source: production")
    print("     - Shared with: Shows 'All environments' or includes PR envs")
    
    print("\n  STEP 4: Test in PR Environment")
    print("  ──────────────────────────────")
    print("  1. Go to a PR environment (e.g., pr-123)")
    print("  2. Click 'Variables' tab")
    print("  3. Look for YOTO_SERVER_CLIENT_ID")
    print("  4. Value should show: ${{shared.YOTO_SERVER_CLIENT_ID}}")
    print("  5. Hover over it to see resolved value")
    
    print("\n  STEP 5: Alternative - Set Directly (Not Recommended)")
    print("  ────────────────────────────────────────────────────")
    print("  If shared variables don't work, temporarily set directly:")
    print("  $ railway variables set YOTO_SERVER_CLIENT_ID='your_value' -e pr-123")
    print("  ⚠️  This is a workaround - proper fix is sharing from production")


def check_github_workflow_config() -> None:
    """Check if GitHub workflows are properly configured."""
    print("\n" + "=" * 80)
    print("8. GitHub Workflow Configuration Check")
    print("=" * 80)
    
    workflow_file = ".github/workflows/railway-pr-checks.yml"
    if os.path.exists(workflow_file):
        print(f"\n✅ Found workflow: {workflow_file}")
        
        with open(workflow_file, 'r') as f:
            content = f.read()
            
        if 'YOTO_SERVER_CLIENT_ID' in content:
            print("✅ Workflow references YOTO_SERVER_CLIENT_ID")
            
            # Check if it's using GitHub secrets
            if '${{ secrets.YOTO_SERVER_CLIENT_ID }}' in content:
                print("✅ Uses GitHub Secrets for YOTO_SERVER_CLIENT_ID")
                print("\n⚠️  NOTE: Workflow sets variable directly, not using shared variables!")
                print("   This is a WORKAROUND for the shared variables issue.")
                print("   Line in workflow:")
                for i, line in enumerate(content.split('\n'), 1):
                    if 'YOTO_SERVER_CLIENT_ID' in line and 'railway variables set' in content[max(0, content.find(line)-200):content.find(line)+200]:
                        print(f"   {i}: {line.strip()}")
        else:
            print("⚠️  Workflow doesn't reference YOTO_SERVER_CLIENT_ID")
    else:
        print(f"❌ Workflow file not found: {workflow_file}")


def main():
    """Main diagnostic function."""
    print("\n" + "=" * 80)
    print("Railway Shared Variables Diagnostic Tool")
    print("Investigating: Why ${{shared.YOTO_SERVER_CLIENT_ID}} is empty in PR environments")
    print("=" * 80)
    
    # Check Railway CLI
    if not check_railway_cli():
        print("\n⚠️  Cannot proceed without Railway CLI access")
        print("Set RAILWAY_TOKEN environment variable and try again")
        sys.exit(1)
    
    # List projects
    project_id = list_projects()
    
    # List environments
    environments = list_environments(project_id)
    
    # Check YOTO_SERVER_CLIENT_ID in each environment
    if environments:
        print("\n" + "=" * 80)
        print("4. Checking YOTO_SERVER_CLIENT_ID in Each Environment")
        print("=" * 80)
        
        for env in environments:
            env_name = env.get('name')
            if env_name:
                check_variable_in_environment(env_name)
    
    # Check shared variables
    check_shared_variables()
    
    # Check variable reference syntax
    check_variable_references()
    
    # Check PR environment setup
    check_pr_environment_setup()
    
    # Provide troubleshooting steps
    provide_troubleshooting_steps()
    
    # Check GitHub workflow
    check_github_workflow_config()
    
    print("\n" + "=" * 80)
    print("Diagnostic Complete")
    print("=" * 80)
    print("\n📊 Summary:")
    print("  1. Check Railway Web UI for shared variable configuration")
    print("  2. Verify YOTO_SERVER_CLIENT_ID is marked as 'shared' from production")
    print("  3. Ensure sharing scope includes PR environments")
    print("  4. GitHub workflow currently sets variables directly as workaround")
    print("\n🔗 Useful Links:")
    print("  - Railway Dashboard: https://railway.app")
    print("  - Shared Variables Docs: https://docs.railway.app/guides/variables#shared-variables")
    print("  - Railway Support: https://help.railway.app")
    print("\n")


if __name__ == "__main__":
    main()
