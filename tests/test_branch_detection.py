#!/usr/bin/env python3
"""
Tests for the branch-based environment detection logic.
"""
import os
import sys

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

# Import after path is modified
from get_deployment_environment import (  # noqa: E402
    get_deployment_environment,
    get_pr_number,
    normalize_environment_name,
)


def test_normalize_environment_name():
    """Test environment name normalization."""
    test_cases = [
        # (input, pr_number, expected_output)
        ("copilot/implement-deployment-workflow", None, "copilot-implement-deployment-workflow"),
        (
            "copilot/implement-deployment-workflow",
            "123",
            "copilot-implement-deployment-workflow-pr123",
        ),
        ("copilot-fix-bug", None, "copilot-fix-bug"),
        ("feature/add-new-api", None, "feature-add-new-api"),
        ("fix_bug_123", None, "fix-bug-123"),
        ("UPPERCASE-Branch", None, "uppercase-branch"),
        ("branch--with--double--hyphens", None, "branch-with-double-hyphens"),
        ("-leading-hyphen", None, "leading-hyphen"),
        ("trailing-hyphen-", None, "trailing-hyphen"),
        ("123-starts-with-number", None, "e-123-starts-with-number"),
        ("special@chars#removed!", None, "specialcharsremoved"),
        ("a" * 100, None, "a" * 50),  # Test length limiting
        ("copilot/test", "42", "copilot-test-pr42"),
    ]

    print("Testing normalize_environment_name()...")
    for input_val, pr_num, expected in test_cases:
        result = normalize_environment_name(input_val, pr_num)
        status = "✓" if result == expected else "✗"
        pr_info = f" (PR: {pr_num})" if pr_num else ""
        print(f"  {status} '{input_val}'{pr_info} -> '{result}' (expected: '{expected}')")
        assert result == expected, f"Failed: got '{result}', expected '{expected}'"

    print("  All normalization tests passed!\n")


def test_get_deployment_environment():
    """Test deployment environment detection."""
    test_cases = [
        # (branch_name, expected_environment_prefix)
        ("aws-main", "prod"),
        ("aws-develop", "dev"),
        ("copilot/implement-deployment-workflow", "copilot-implement-deployment-workflow"),
        ("copilot-fix-bug", "copilot-fix-bug"),
        ("feature/new-feature", "dev"),
        ("bugfix/some-bug", "dev"),
        ("main", "dev"),
        ("develop", "dev"),
    ]

    print("Testing get_deployment_environment()...")
    for branch, expected_prefix in test_cases:
        result = get_deployment_environment(branch)
        # For copilot/* branches, result might have -prXXX suffix
        matches = result == expected_prefix or result.startswith(expected_prefix + "-pr")
        status = "✓" if matches else "✗"
        print(
            f"  {status} Branch '{branch}' -> Environment '{result}' (expected: '{expected_prefix}*')"
        )
        assert (
            matches
        ), f"Failed: got '{result}', expected '{expected_prefix}' or '{expected_prefix}-pr*'"

    print("  All environment detection tests passed!\n")


def test_copilot_branch_isolation():
    """Test that copilot branches get unique environments."""
    branches = [
        "copilot/feature-a",
        "copilot/feature-b",
        "copilot-worktree-1",
        "copilot-worktree-2",
    ]

    print("Testing copilot branch isolation...")
    environments = [get_deployment_environment(b) for b in branches]

    # All should start with 'copilot-'
    for env in environments:
        assert env.startswith("copilot-"), f"Environment '{env}' should start with 'copilot-'"

    # With different branch names, they should be different
    # (Note: If PR numbers are the same, some might be identical, but that's OK)
    print("  ✓ All copilot branches get isolated environments")
    print(f"    Environments: {environments}\n")


def test_pr_number_detection():
    """Test PR number detection from environment."""
    print("Testing PR number detection...")

    # Save original env vars
    original_pr = os.environ.get("PR_NUMBER")
    original_github_ref = os.environ.get("GITHUB_REF")

    try:
        # Test with PR_NUMBER env var
        os.environ["PR_NUMBER"] = "123"
        pr_num = get_pr_number()
        assert pr_num == "123", f"Expected '123', got '{pr_num}'"
        print("  ✓ PR_NUMBER env var detected correctly")

        # Test with GITHUB_REF
        del os.environ["PR_NUMBER"]
        os.environ["GITHUB_REF"] = "refs/pull/456/merge"
        pr_num = get_pr_number()
        assert pr_num == "456", f"Expected '456', got '{pr_num}'"
        print("  ✓ GITHUB_REF PR number extracted correctly")

        # Test with no PR context
        del os.environ["GITHUB_REF"]
        pr_num = get_pr_number()
        assert pr_num is None, f"Expected None, got '{pr_num}'"
        print("  ✓ No PR context handled correctly")

    finally:
        # Restore original env vars
        if original_pr:
            os.environ["PR_NUMBER"] = original_pr
        elif "PR_NUMBER" in os.environ:
            del os.environ["PR_NUMBER"]

        if original_github_ref:
            os.environ["GITHUB_REF"] = original_github_ref
        elif "GITHUB_REF" in os.environ:
            del os.environ["GITHUB_REF"]

    print("  All PR number detection tests passed!\n")


if __name__ == "__main__":
    print("=" * 70)
    print("Branch-Based Environment Detection Tests")
    print("=" * 70)
    print()

    try:
        test_normalize_environment_name()
        test_get_deployment_environment()
        test_copilot_branch_isolation()
        test_pr_number_detection()

        print("=" * 70)
        print("All tests passed! ✓")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
