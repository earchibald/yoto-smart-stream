# Railway Development Environment Locks

This directory contains lock files for coordinating access to the shared development Railway environment.

The lock file prevents multiple Copilot or PR sessions from deploying simultaneously and interfering with each other.

Lock files are automatically managed by the `railway-development-shared.yml` workflow.
