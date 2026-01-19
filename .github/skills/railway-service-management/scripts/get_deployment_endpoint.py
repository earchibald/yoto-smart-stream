#!/usr/bin/env python3
"""
Get Railway Deployment Endpoint URL

This script uses the Railway CLI to describe deployments and retrieve endpoint URLs.
It provides a simple interface to get deployment information for a specific environment
or service.

Usage:
    # Get endpoint for default/linked service
    python get_deployment_endpoint.py

    # Get endpoint for specific environment
    python get_deployment_endpoint.py --environment production

    # Get endpoint for specific service and environment
    python get_deployment_endpoint.py --service yoto-smart-stream --environment staging

    # Get latest deployment info (JSON)
    python get_deployment_endpoint.py --json

    # List all deployments
    python get_deployment_endpoint.py --list

    # Get deployment by ID
    python get_deployment_endpoint.py --deployment-id <ID>

Environment Variables:
    RAILWAY_TOKEN - Optional Railway API token for authentication
"""

import argparse
import json
import subprocess
import sys
from typing import Any, Optional


class RailwayDeploymentInfo:
    """Get deployment information using Railway CLI."""

    def __init__(self):
        """Initialize and check Railway CLI availability."""
        self._check_railway_cli()

    def _check_railway_cli(self):
        """Verify Railway CLI is installed and available."""
        try:
            result = subprocess.run(
                ["railway", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError("Railway CLI is not working properly")
        except FileNotFoundError as e:
            raise RuntimeError(
                "Railway CLI is not installed. Install with: npm i -g @railway/cli"
            ) from e
        except subprocess.TimeoutExpired as e:
            raise RuntimeError("Railway CLI check timed out") from e
        except Exception as e:
            raise RuntimeError(f"Error checking Railway CLI: {e}") from e

    def _run_railway_command(self, args: list[str]) -> dict[str, Any]:
        """Run a Railway CLI command and return JSON output."""
        cmd = ["railway"] + args

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                raise RuntimeError(f"Railway command failed: {error_msg}")

            # Parse JSON output
            output = result.stdout.strip()
            if not output:
                return {}

            try:
                parsed: dict[str, Any] = json.loads(output)
                return parsed
            except json.JSONDecodeError:
                # If not JSON, return as text in a dict
                return {"output": output}

        except subprocess.TimeoutExpired as e:
            raise RuntimeError("Railway command timed out") from e
        except Exception as e:
            raise RuntimeError(f"Error running Railway command: {e}") from e

    def get_status(self, environment: Optional[str] = None) -> dict[str, Any]:
        """Get current project/environment status.

        Args:
            environment: Optional environment name to filter (filtering happens post-fetch)

        Returns:
            Dict containing status information including:
            - project: Project information
            - service: Service information
            - environment: Environment information
            - deployments: Recent deployment information

        Note:
            The railway status command doesn't support --environment flag,
            so we fetch all environments and filter in the script if needed.
        """
        args = ["status", "--json"]
        # Note: status doesn't support --environment flag

        result = self._run_railway_command(args)

        # If environment is specified, filter the response to only that environment
        if environment and result and "environments" in result:
            environments = result.get("environments", {})
            if isinstance(environments, dict) and "edges" in environments:
                edges = environments["edges"]
                filtered_edges = [
                    edge for edge in edges if edge.get("node", {}).get("name") == environment
                ]
                if filtered_edges:
                    result["environments"]["edges"] = filtered_edges
                else:
                    # Environment not found
                    result["environments"]["edges"] = []

        return result

    def list_deployments(
        self, service: Optional[str] = None, environment: Optional[str] = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        """List deployments for a service.

        Args:
            service: Optional service name or ID
            environment: Optional environment name
            limit: Maximum number of deployments to return (default: 20)

        Returns:
            List of deployment dictionaries
        """
        args = ["deployment", "list", "--json", "--limit", str(limit)]

        if service:
            args.extend(["--service", service])
        if environment:
            args.extend(["--environment", environment])

        result = self._run_railway_command(args)

        # Railway CLI returns deployments in different formats
        # Try to normalize the response
        if isinstance(result, list):
            deployments: list[dict[str, Any]] = result
            return deployments
        elif isinstance(result, dict) and "deployments" in result:
            deployments_list: list[dict[str, Any]] = result["deployments"]
            return deployments_list
        else:
            return [result] if result else []

    def get_latest_deployment(
        self, service: Optional[str] = None, environment: Optional[str] = None
    ) -> Optional[dict[str, Any]]:
        """Get the latest deployment for a service.

        Args:
            service: Optional service name or ID
            environment: Optional environment name

        Returns:
            Dict containing deployment information, or None if no deployments found
        """
        deployments = self.list_deployments(service, environment, limit=1)
        return deployments[0] if deployments else None

    def extract_endpoint_url(self, data: dict[str, Any]) -> Optional[str]:
        """Extract endpoint URL from deployment or status information.

        Args:
            data: Deployment or status dictionary from Railway CLI

        Returns:
            Endpoint URL string, or None if not found
        """
        # Case 1: Direct URL fields (deployment response)
        if "url" in data:
            url = data["url"]
            if url and isinstance(url, str):
                url_str: str = url
                if not url_str.startswith("http"):
                    return f"https://{url_str}"
                return url_str
            return None

        # Case 2: staticUrl field
        if "staticUrl" in data:
            static_url = data["staticUrl"]
            if static_url and isinstance(static_url, str):
                static_url_str: str = static_url
                if not static_url_str.startswith("http"):
                    return f"https://{static_url_str}"
                return static_url_str
            return None

        # Case 3: domain field (simple string)
        if "domain" in data and isinstance(data["domain"], str):
            domain: str = data["domain"]
            if domain and not domain.startswith("http"):
                return f"https://{domain}"
            return domain

        # Case 4: domains object (from status response)
        if "domains" in data:
            domains_obj = data["domains"]

            # Try serviceDomains array
            if isinstance(domains_obj, dict):
                service_domains = domains_obj.get("serviceDomains", [])
                if isinstance(service_domains, list) and service_domains:
                    first_domain = service_domains[0]
                    if isinstance(first_domain, dict) and "domain" in first_domain:
                        domain_val = first_domain["domain"]
                        if isinstance(domain_val, str):
                            if domain_val and not domain_val.startswith("http"):
                                return f"https://{domain_val}"
                            return domain_val

            # Try domains as simple array
            elif isinstance(domains_obj, list) and domains_obj:
                domain_item = domains_obj[0]
                if isinstance(domain_item, dict) and "domain" in domain_item:
                    domain_item = domain_item["domain"]
                if isinstance(domain_item, str):
                    if domain_item and not domain_item.startswith("http"):
                        return f"https://{domain_item}"
                    return domain_item

        # Case 5: Railway status response structure (environments -> serviceInstances)
        if "environments" in data:
            environments = data.get("environments", {})
            if isinstance(environments, dict) and "edges" in environments:
                edges = environments["edges"]
                if isinstance(edges, list) and edges:
                    # Get first environment
                    env_node = edges[0].get("node", {})
                    service_instances = env_node.get("serviceInstances", {})
                    if isinstance(service_instances, dict) and "edges" in service_instances:
                        si_edges = service_instances["edges"]
                        if isinstance(si_edges, list) and si_edges:
                            # Get first service instance
                            si_node = si_edges[0].get("node", {})
                            # Recursively extract from service instance
                            return self.extract_endpoint_url(si_node)

        return None

    def get_endpoint_url(
        self, service: Optional[str] = None, environment: Optional[str] = None
    ) -> Optional[str]:
        """Get the endpoint URL for a deployment.

        This is the main convenience method that gets the latest deployment
        and extracts its endpoint URL.

        Args:
            service: Optional service name or ID
            environment: Optional environment name

        Returns:
            Endpoint URL string, or None if not found
        """
        # First try to get from status (faster for linked projects)
        try:
            status = self.get_status(environment)
            if status:
                url = self.extract_endpoint_url(status)
                if url:
                    return url
        except Exception:
            # If status fails, try listing deployments
            pass

        # Fall back to listing deployments
        deployment = self.get_latest_deployment(service, environment)
        if deployment:
            return self.extract_endpoint_url(deployment)

        return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Get Railway deployment endpoint URL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("-s", "--service", help="Service name or ID (defaults to linked service)")
    parser.add_argument(
        "-e", "--environment", help="Environment name (defaults to linked environment)"
    )
    parser.add_argument(
        "--deployment-id", help="Get specific deployment by ID (not implemented yet)"
    )
    parser.add_argument(
        "--list", action="store_true", help="List all deployments instead of getting endpoint"
    )
    parser.add_argument(
        "--limit", type=int, default=20, help="Maximum number of deployments to list (default: 20)"
    )
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument(
        "--url-only", action="store_true", help="Output only the URL (useful for scripts)"
    )

    args = parser.parse_args()

    try:
        client = RailwayDeploymentInfo()

        if args.list:
            # List deployments
            deployments = client.list_deployments(args.service, args.environment, args.limit)

            if args.json:
                print(json.dumps(deployments, indent=2))
            else:
                if not deployments:
                    print("No deployments found.")
                    return

                print(f"\n=== Deployments ({len(deployments)}) ===\n")
                for i, deploy in enumerate(deployments, 1):
                    print(f"{i}. Deployment ID: {deploy.get('id', 'N/A')}")
                    print(f"   Status: {deploy.get('status', 'N/A')}")
                    print(f"   Created: {deploy.get('createdAt', 'N/A')}")
                    url = client.extract_endpoint_url(deploy)
                    if url:
                        print(f"   URL: {url}")
                    print()

        else:
            # Get endpoint URL
            if args.deployment_id:
                print("Error: --deployment-id is not yet implemented", file=sys.stderr)
                sys.exit(1)

            url = client.get_endpoint_url(args.service, args.environment)

            if not url:
                if args.json:
                    print(json.dumps({"error": "No endpoint URL found"}))
                else:
                    print("Error: No endpoint URL found", file=sys.stderr)
                    print("\nTroubleshooting:", file=sys.stderr)
                    print("1. Make sure you're linked to a project: railway link", file=sys.stderr)
                    print(
                        "2. Check if the service has a deployment: railway deployment list",
                        file=sys.stderr,
                    )
                    print("3. Verify the environment: railway status", file=sys.stderr)
                sys.exit(1)

            if args.url_only:
                print(url)
            elif args.json:
                print(
                    json.dumps(
                        {"url": url, "service": args.service, "environment": args.environment}
                    )
                )
            else:
                print(f"Endpoint URL: {url}")
                if args.service:
                    print(f"Service: {args.service}")
                if args.environment:
                    print(f"Environment: {args.environment}")

    except RuntimeError as e:
        if args.json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        if args.json:
            print(json.dumps({"error": f"Unexpected error: {str(e)}"}))
        else:
            print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
