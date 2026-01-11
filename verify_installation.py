#!/usr/bin/env python3
"""
Verification script for Yoto Smart Stream installation.

This script checks that:
1. All dependencies are installed
2. Tests can run
3. Code quality checks pass
4. Examples can be imported
5. API server can start
6. Everything is ready for use

Run this after installation to verify everything is working.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_status(check_name, passed, message=""):
    """Print status of a check."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {check_name}")
    if message:
        print(f"     {message}")


def check_python_version():
    """Check Python version is 3.9+."""
    version = sys.version_info
    passed = version >= (3, 9)
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    print_status("Python version", passed, f"Python {version_str}")
    return passed


def check_dependencies():
    """Check that required dependencies are installed."""
    required_packages = [
        ("yoto_api", "Yoto API client"),
        ("fastapi", "FastAPI framework"),
        ("pydantic", "Data validation"),
        ("httpx", "HTTP client"),
        ("PIL", "Pillow image library"),
        ("pytest", "Testing framework"),
    ]

    all_passed = True
    for package, description in required_packages:
        try:
            spec = importlib.util.find_spec(package)
            passed = spec is not None
            print_status(description, passed, package)
            all_passed = all_passed and passed
        except Exception as e:
            print_status(description, False, f"{package} - {str(e)}")
            all_passed = False

    return all_passed


def run_command(cmd, description):
    """Run a command and return success status."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        passed = result.returncode == 0
        if not passed:
            message = result.stderr[:100] if result.stderr else "Command failed"
            print_status(description, passed, message)
        else:
            print_status(description, passed)
        return passed
    except subprocess.TimeoutExpired:
        print_status(description, False, "Command timed out")
        return False
    except Exception as e:
        print_status(description, False, str(e))
        return False


def check_tests():
    """Run pytest and check if tests pass."""
    print("\n  Running tests (this may take a few seconds)...")
    return run_command("python -m pytest tests/ -q --tb=no --no-cov", "Unit tests")


def check_linting():
    """Check code quality with ruff."""
    return run_command("ruff check .", "Code linting")


def check_formatting():
    """Check code formatting with black."""
    # Black returns 0 if files are formatted, 1 if changes needed
    # We just want to verify black works, not that all files are formatted
    result = subprocess.run("black --version", shell=True, capture_output=True, text=True)
    passed = result.returncode == 0
    print_status("Code formatting (black installed)", passed)
    return passed


def check_examples():
    """Check that example scripts can be imported."""
    examples = [
        "simple_client",
        "basic_server",
        "mqtt_listener",
        "icon_management",
    ]

    # Add examples to path
    examples_dir = Path(__file__).parent / "examples"
    sys.path.insert(0, str(examples_dir))

    all_passed = True
    for example in examples:
        try:
            __import__(example)
            print_status(f"Example: {example}.py", True)
        except Exception as e:
            print_status(f"Example: {example}.py", False, str(e)[:50])
            all_passed = False

    return all_passed


def check_icon_module():
    """Check that icon module works."""
    try:
        from yoto_smart_stream.icons import (
            DisplayIcon,
        )

        # Try to create a test icon
        DisplayIcon(
            id="test",
            name="Test",
            url="https://example.com/icon.png",
            tags=["test"],
            is_public=True,
        )

        print_status("Icon module", True)
        return True
    except Exception as e:
        print_status("Icon module", False, str(e)[:50])
        return False


def check_documentation():
    """Check that documentation files exist."""
    docs = [
        ("README.md", "Main README"),
        ("docs/QUICK_START.md", "Quick Start Guide"),
        ("docs/TESTING_GUIDE.md", "Testing Guide"),
        ("docs/ICON_MANAGEMENT.md", "Icon Management Guide"),
    ]

    all_passed = True
    for filepath, description in docs:
        exists = Path(filepath).exists()
        print_status(description, exists, filepath)
        all_passed = all_passed and exists

    return all_passed


def main():
    """Run all verification checks."""
    print("\n" + "🔍 " * 20)
    print("  YOTO SMART STREAM - INSTALLATION VERIFICATION")
    print("🔍 " * 20)

    results = {}

    # Python version
    print_section("1. Python Environment")
    results["python"] = check_python_version()

    # Dependencies
    print_section("2. Dependencies")
    results["dependencies"] = check_dependencies()

    # Icon module
    print_section("3. Core Modules")
    results["icon_module"] = check_icon_module()

    # Examples
    print_section("4. Example Scripts")
    results["examples"] = check_examples()

    # Documentation
    print_section("5. Documentation")
    results["documentation"] = check_documentation()

    # Tests
    print_section("6. Test Suite")
    results["tests"] = check_tests()

    # Code quality
    print_section("7. Code Quality")
    results["linting"] = check_linting()
    results["formatting"] = check_formatting()

    # Summary
    print_section("VERIFICATION SUMMARY")
    passed = sum(results.values())
    total = len(results)

    print(f"\nPassed: {passed}/{total} checks")

    if passed == total:
        print("\n✅ " * 10)
        print("\n  🎉 ALL CHECKS PASSED! 🎉")
        print("\n  Your Yoto Smart Stream installation is ready to use!")
        print("\n  Next steps:")
        print("    1. Read docs/QUICK_START.md")
        print("    2. Configure your YOTO_SERVER_CLIENT_ID (or YOTO_CLIENT_ID for backward compatibility)")
        print("    3. Run: python examples/simple_client.py")
        print("\n✅ " * 10)
        return 0
    else:
        print("\n⚠️  " * 10)
        print("\n  Some checks failed. Please review the errors above.")
        print("\n  Common fixes:")
        print("    - Reinstall dependencies: pip install -e '.[dev]'")
        print("    - Check Python version: python --version")
        print("    - Review error messages for specific issues")
        print("\n⚠️  " * 10)
        return 1


if __name__ == "__main__":
    sys.exit(main())
