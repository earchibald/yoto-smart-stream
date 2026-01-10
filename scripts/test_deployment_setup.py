#!/usr/bin/env python3
"""
Test script to verify Railway deployment setup

This script checks that all necessary files for Railway deployment exist
and are configured correctly.
"""

import os
import sys
from pathlib import Path


def test_railway_cli_installed():
    """Check if Railway CLI is installed"""
    import subprocess
    try:
        result = subprocess.run(
            ["which", "railway"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            print("✅ Railway CLI is installed")
            version_result = subprocess.run(
                ["railway", "--version"],
                capture_output=True,
                text=True,
                check=False
            )
            print(version_result.stdout.strip())
            return True
        else:
            print("❌ Railway CLI is NOT installed")
            print("   Run: npm i -g @railway/cli")
            return False
    except Exception as e:
        print(f"❌ Error checking Railway CLI: {e}")
        return False


def test_railway_toml_exists():
    """Check if railway.toml exists"""
    if Path("railway.toml").exists():
        print("✅ railway.toml exists")
        return True
    else:
        print("❌ railway.toml does NOT exist")
        return False


def test_deploy_script_exists():
    """Check if deploy.sh script exists and is executable"""
    script_path = Path("scripts/deploy.sh")
    if script_path.exists():
        print(f"✅ deploy.sh exists at {script_path}")
        if os.access(script_path, os.X_OK):
            print("✅ deploy.sh is executable")
            return True
        else:
            print("⚠️  deploy.sh is not executable")
            print("   Run: chmod +x scripts/deploy.sh")
            return False
    else:
        print("❌ deploy.sh does NOT exist")
        return False


def test_github_workflow_exists():
    """Check if GitHub Actions workflow exists"""
    workflow_path = Path(".github/workflows/railway-deploy.yml")
    if workflow_path.exists():
        print(f"✅ GitHub Actions workflow exists at {workflow_path}")
        return True
    else:
        print("❌ GitHub Actions workflow does NOT exist")
        return False


def test_documentation_exists():
    """Check if deployment documentation exists"""
    doc_path = Path("docs/RAILWAY_DEPLOYMENT.md")
    if doc_path.exists():
        print(f"✅ Deployment documentation exists at {doc_path}")
        return True
    else:
        print("❌ Deployment documentation does NOT exist")
        return False


def test_health_endpoint():
    """Check if basic_server has health endpoint"""
    server_path = Path("examples/basic_server.py")
    if server_path.exists():
        content = server_path.read_text()
        if '@app.get("/health"' in content or '@app.get(\'/health\'' in content:
            print("✅ Health endpoint exists in basic_server.py")
            return True
        else:
            print("⚠️  Health endpoint not found in basic_server.py")
            return False
    else:
        print("❌ basic_server.py does NOT exist")
        return False


def test_env_example_updated():
    """Check if .env.example has Railway variables"""
    env_path = Path(".env.example")
    if env_path.exists():
        content = env_path.read_text()
        if "RAILWAY_TOKEN" in content and "PUBLIC_URL" in content:
            print("✅ .env.example includes Railway variables")
            return True
        else:
            print("⚠️  .env.example missing Railway variables")
            return False
    else:
        print("❌ .env.example does NOT exist")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Railway Deployment Setup Verification")
    print("=" * 60)
    print()
    
    tests = [
        test_railway_cli_installed,
        test_railway_toml_exists,
        test_deploy_script_exists,
        test_github_workflow_exists,
        test_documentation_exists,
        test_health_endpoint,
        test_env_example_updated,
    ]
    
    results = []
    for test in tests:
        print(f"\nRunning: {test.__doc__}")
        print("-" * 60)
        results.append(test())
        print()
    
    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All checks passed! Railway deployment is ready.")
        print("\nNext steps:")
        print("  1. Authenticate: railway login")
        print("  2. Link project: railway link")
        print("  3. Test deploy: ./scripts/deploy.sh staging --dry-run")
        print("  4. Deploy: ./scripts/deploy.sh staging")
        return 0
    else:
        print(f"\n⚠️  {total - passed} check(s) failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
