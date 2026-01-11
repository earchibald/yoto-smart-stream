"""Environment variable logging utilities."""

import os
from typing import Callable


def log_environment_variables(output_fn: Callable[[str], None]) -> None:
    """
    Log all environment variables for debugging Railway variable initialization.

    Args:
        output_fn: Function to use for output (e.g., print or logger.info)
    """
    output_fn("=" * 80)
    output_fn("Environment Variables:")
    output_fn("=" * 80)

    # Get all environment variables and sort them for easier reading
    env_vars = sorted(os.environ.items())

    # Mask sensitive values
    sensitive_keys = {
        'TOKEN', 'SECRET', 'PASSWORD', 'KEY', 'CREDENTIAL',
        'AUTH', 'API_KEY', 'REFRESH_TOKEN', 'ACCESS_TOKEN'
    }

    for key, value in env_vars:
        # Check if key contains sensitive information
        is_sensitive = any(sensitive in key.upper() for sensitive in sensitive_keys)

        if is_sensitive:
            # Show only first and last 4 characters for sensitive values
            if len(value) > 8:
                masked_value = f"{value[:4]}...{value[-4:]}"
            else:
                masked_value = "***"
            output_fn(f"  {key}={masked_value}")
        else:
            output_fn(f"  {key}={value}")

    output_fn("=" * 80)
