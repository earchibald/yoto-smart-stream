#!/usr/bin/env python3
"""
Validate Railway PR Environment

This script validates that a Railway PR environment is properly configured
and functioning correctly. It can be run locally or as part of CI/CD.

Usage:
    # Test local development
    python scripts/validate_pr_environment.py http://localhost:8000

    # Test Railway PR environment
    python scripts/validate_pr_environment.py https://yoto-smart-stream-pr-42.up.railway.app

    # Auto-detect from environment
    python scripts/validate_pr_environment.py
"""

import argparse
import json
import os
import sys
import time
from typing import Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class Colors:
    """ANSI color codes for terminal output."""

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def log_info(message: str) -> None:
    """Log info message."""
    print(f"{Colors.BLUE}ℹ{Colors.RESET} {message}")


def log_success(message: str) -> None:
    """Log success message."""
    print(f"{Colors.GREEN}✓{Colors.RESET} {message}")


def log_warning(message: str) -> None:
    """Log warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {message}")


def log_error(message: str) -> None:
    """Log error message."""
    print(f"{Colors.RED}✗{Colors.RESET} {message}")


def log_header(message: str) -> None:
    """Log section header."""
    print(f"\n{Colors.BOLD}{message}{Colors.RESET}")


def make_request(url: str, timeout: int = 10) -> Tuple[int, Optional[Dict]]:
    """
    Make HTTP request and return status code and JSON response.

    Args:
        url: URL to request
        timeout: Request timeout in seconds

    Returns:
        Tuple of (status_code, response_data)
    """
    try:
        req = Request(url)
        req.add_header("User-Agent", "Railway-PR-Validator/1.0")
        with urlopen(req, timeout=timeout) as response:
            status = response.status
            data = None
            if response.headers.get("Content-Type", "").startswith("application/json"):
                data = json.loads(response.read().decode("utf-8"))
            return status, data
    except HTTPError as e:
        return e.code, None
    except URLError as e:
        log_error(f"Connection failed: {e.reason}")
        return 0, None
    except Exception as e:
        log_error(f"Request failed: {str(e)}")
        return 0, None


def wait_for_deployment(base_url: str, max_attempts: int = 30, delay: int = 10) -> bool:
    """
    Wait for deployment to be ready.

    Args:
        base_url: Base URL of the service
        max_attempts: Maximum number of attempts
        delay: Delay between attempts in seconds

    Returns:
        True if deployment is ready, False otherwise
    """
    log_info(f"Waiting for deployment (max {max_attempts * delay}s)...")

    for attempt in range(1, max_attempts + 1):
        log_info(f"Attempt {attempt}/{max_attempts}")
        status, _ = make_request(f"{base_url}/health", timeout=5)

        if status == 200:
            log_success("Deployment is ready!")
            return True

        if attempt < max_attempts:
            time.sleep(delay)

    return False


def validate_health_endpoint(base_url: str) -> bool:
    """Validate the health endpoint."""
    log_header("1. Testing Health Endpoint")

    status, data = make_request(f"{base_url}/health")

    if status != 200:
        log_error(f"Health check failed with status {status}")
        return False

    if not data:
        log_error("Health check returned no data")
        return False

    log_success(f"Health check passed: {data.get('status')}")
    log_info(f"  Version: {data.get('version')}")
    log_info(f"  Environment: {data.get('environment')}")
    log_info(f"  MQTT Enabled: {data.get('mqtt_enabled')}")
    log_info(f"  Audio Files: {data.get('audio_files')}")

    return True


def validate_root_endpoint(base_url: str) -> bool:
    """Validate the root endpoint."""
    log_header("2. Testing Root Endpoint")

    status, data = make_request(base_url)

    if status != 200:
        log_error(f"Root endpoint failed with status {status}")
        return False

    if not data:
        log_error("Root endpoint returned no data")
        return False

    log_success(f"Root endpoint passed: {data.get('status')}")
    log_info(f"  Name: {data.get('name')}")
    log_info(f"  Version: {data.get('version')}")
    log_info(f"  Environment: {data.get('environment')}")

    features = data.get("features", {})
    log_info("  Features:")
    for feature, enabled in features.items():
        status_icon = "✓" if enabled else "✗"
        log_info(f"    {status_icon} {feature}: {enabled}")

    return True


def validate_openapi_docs(base_url: str) -> bool:
    """Validate OpenAPI documentation endpoint."""
    log_header("3. Testing API Documentation")

    status, _ = make_request(f"{base_url}/docs")

    if status != 200:
        log_warning(f"API docs endpoint returned status {status}")
        return False

    log_success("API documentation is accessible")
    log_info(f"  Docs URL: {base_url}/docs")

    return True


def validate_railway_config() -> bool:
    """Validate Railway configuration file."""
    log_header("4. Validating Railway Configuration")

    config_path = "railway.toml"
    if not os.path.exists(config_path):
        log_error(f"Railway config not found: {config_path}")
        return False

    log_success("Railway config file exists")

    # Read and validate config
    with open(config_path, "r") as f:
        content = f.read()

    required_sections = [
        "[build]",
        "[deploy]",
        "startCommand",
        "healthcheckPath",
    ]

    all_present = True
    for section in required_sections:
        if section in content:
            log_success(f"  ✓ Found: {section}")
        else:
            log_error(f"  ✗ Missing: {section}")
            all_present = False

    # Validate health check path
    if '/health"' in content or "/health'" in content:
        log_success("  ✓ Health check path configured")
    else:
        log_warning("  ⚠ Health check path may not be configured")

    return all_present


def validate_github_workflow() -> bool:
    """Validate GitHub Actions workflow for PR checks."""
    log_header("5. Validating GitHub Workflow")

    workflow_path = ".github/workflows/railway-pr-checks.yml"
    if not os.path.exists(workflow_path):
        log_warning(f"PR checks workflow not found: {workflow_path}")
        return False

    log_success("PR checks workflow exists")

    # Read and validate workflow
    with open(workflow_path, "r") as f:
        content = f.read()

    checks = [
        ("pull_request trigger", "on:\n  pull_request:" in content),
        ("health check test", "health" in content.lower()),
        ("PR comment", "createComment" in content or "comment" in content.lower()),
    ]

    all_passed = True
    for check_name, passed in checks:
        if passed:
            log_success(f"  ✓ {check_name}")
        else:
            log_warning(f"  ⚠ {check_name} not found")
            all_passed = False

    return all_passed


def detect_pr_url() -> Optional[str]:
    """
    Detect PR environment URL from environment variables.

    Returns:
        PR environment URL or None
    """
    # Check for GitHub Actions environment
    pr_number = os.environ.get("PR_NUMBER") or os.environ.get("GITHUB_PR_NUMBER")
    if pr_number:
        return f"https://yoto-smart-stream-pr-{pr_number}.up.railway.app"

    # Check for Railway environment
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT_NAME")
    if railway_env and railway_env.startswith("pr-"):
        pr_number = railway_env.replace("pr-", "")
        return f"https://yoto-smart-stream-pr-{pr_number}.up.railway.app"

    return None


def main() -> int:
    """Main validation function."""
    parser = argparse.ArgumentParser(
        description="Validate Railway PR Environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test local development
  python scripts/validate_pr_environment.py http://localhost:8000

  # Test Railway PR environment
  python scripts/validate_pr_environment.py https://yoto-smart-stream-pr-42.up.railway.app

  # Auto-detect from environment
  python scripts/validate_pr_environment.py
        """,
    )
    parser.add_argument(
        "base_url",
        nargs="?",
        help="Base URL of the service (auto-detected if not provided)",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for deployment to be ready before testing",
    )
    parser.add_argument(
        "--skip-config",
        action="store_true",
        help="Skip local configuration validation",
    )

    args = parser.parse_args()

    # Determine base URL
    base_url = args.base_url
    if not base_url:
        base_url = detect_pr_url()
        if base_url:
            log_info(f"Auto-detected PR URL: {base_url}")
        else:
            log_error("Could not detect PR URL. Please provide base_url argument.")
            return 1

    # Remove trailing slash
    base_url = base_url.rstrip("/")

    print(f"{Colors.BOLD}Railway PR Environment Validation{Colors.RESET}")
    print(f"Target: {base_url}\n")

    # Wait for deployment if requested
    if args.wait:
        if not wait_for_deployment(base_url):
            log_error("Deployment did not become ready in time")
            return 1

    # Run validations
    results = []

    # API endpoint tests
    results.append(("Health Endpoint", validate_health_endpoint(base_url)))
    results.append(("Root Endpoint", validate_root_endpoint(base_url)))
    results.append(("API Documentation", validate_openapi_docs(base_url)))

    # Configuration tests (skip if running remotely)
    if not args.skip_config:
        results.append(("Railway Config", validate_railway_config()))
        results.append(("GitHub Workflow", validate_github_workflow()))

    # Summary
    log_header("Validation Summary")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        if result:
            log_success(f"{name}")
        else:
            log_error(f"{name}")

    print(f"\n{Colors.BOLD}Results: {passed}/{total} checks passed{Colors.RESET}")

    if passed == total:
        log_success("All validations passed! ✨")
        return 0
    else:
        log_warning(f"{total - passed} validation(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
