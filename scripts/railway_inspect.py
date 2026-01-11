#!/usr/bin/env python3
"""
Railway Service Inspector
Direct GraphQL API access for Railway service inspection and troubleshooting.

This script bypasses the Railway CLI (which has authentication issues) and uses
the Railway GraphQL API directly with RAILWAY_API_TOKEN for:
- Listing projects and services
- Inspecting deployments and their status
- Retrieving deployment logs
- Checking environment variables
- Monitoring service health

Usage:
    # List all projects
    python railway_inspect.py list-projects
    
    # List services in a project
    python railway_inspect.py list-services --project-id <PROJECT_ID>
    
    # Get deployment logs
    python railway_inspect.py logs --deployment-id <DEPLOYMENT_ID> [--limit 100]
    
    # Get recent deployments
    python railway_inspect.py deployments --project-id <PROJECT_ID> --environment <ENV_NAME>
    
    # Inspect service health
    python railway_inspect.py health --project-id <PROJECT_ID> --service-id <SERVICE_ID>
    
    # Interactive mode (finds yoto-smart-stream automatically)
    python railway_inspect.py interactive

Environment Variables:
    RAILWAY_API_TOKEN - Required for authentication
"""

import os
import sys
import json
import argparse
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    import requests
except ImportError:
    print("Error: requests library not installed. Install with: pip install requests")
    sys.exit(1)


class RailwayInspector:
    """Direct Railway GraphQL API client for service inspection."""
    
    GRAPHQL_ENDPOINT = "https://backboard.railway.com/graphql/v2"
    
    def __init__(self, api_token: Optional[str] = None):
        """Initialize with Railway API token."""
        self.api_token = api_token or os.environ.get("RAILWAY_API_TOKEN")
        if not self.api_token:
            raise ValueError(
                "RAILWAY_API_TOKEN not found. Set it as an environment variable or pass it to the constructor."
            )
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
    
    def _query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Execute a GraphQL query."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        response = requests.post(
            self.GRAPHQL_ENDPOINT,
            headers=self.headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"GraphQL request failed: {response.status_code} - {response.text}")
        
        data = response.json()
        if "errors" in data:
            raise Exception(f"GraphQL errors: {json.dumps(data['errors'], indent=2)}")
        
        return data.get("data", {})
    
    def list_projects(self) -> List[Dict]:
        """List all Railway projects."""
        query = """
        query {
            projects {
                edges {
                    node {
                        id
                        name
                        description
                        createdAt
                    }
                }
            }
        }
        """
        data = self._query(query)
        return [edge["node"] for edge in data.get("projects", {}).get("edges", [])]
    
    def get_project_services(self, project_id: str) -> Dict:
        """Get all services in a project."""
        query = """
        query($projectId: String!) {
            project(id: $projectId) {
                id
                name
                services {
                    edges {
                        node {
                            id
                            name
                            createdAt
                        }
                    }
                }
                environments {
                    edges {
                        node {
                            id
                            name
                        }
                    }
                }
            }
        }
        """
        data = self._query(query, {"projectId": project_id})
        return data.get("project", {})
    
    def get_deployments(
        self,
        project_id: str,
        environment_id: Optional[str] = None,
        service_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Get recent deployments."""
        query = """
        query($input: DeploymentListInput!, $limit: Int!) {
            deployments(first: $limit, input: $input) {
                edges {
                    node {
                        id
                        status
                        createdAt
                        staticUrl
                        meta
                    }
                }
            }
        }
        """
        
        input_params = {"projectId": project_id}
        if environment_id:
            input_params["environmentId"] = environment_id
        if service_id:
            input_params["serviceId"] = service_id
        
        variables = {"input": input_params, "limit": limit}
        data = self._query(query, variables)
        return [edge["node"] for edge in data.get("deployments", {}).get("edges", [])]
    
    def get_deployment_logs(self, deployment_id: str, limit: int = 100) -> List[Dict]:
        """Get logs for a specific deployment."""
        query = """
        query($deploymentId: String!, $limit: Int!) {
            deploymentLogs(deploymentId: $deploymentId, limit: $limit) {
                message
                timestamp
                severity
            }
        }
        """
        variables = {"deploymentId": deployment_id, "limit": limit}
        data = self._query(query, variables)
        return data.get("deploymentLogs", [])
    
    def get_service_variables(self, service_id: str, environment_id: str) -> Dict:
        """Get environment variables for a service."""
        query = """
        query($serviceId: String!, $environmentId: String!) {
            variables(serviceId: $serviceId, environmentId: $environmentId)
        }
        """
        variables = {"serviceId": service_id, "environmentId": environment_id}
        data = self._query(query, variables)
        return data.get("variables", {})
    
    def find_yoto_project(self) -> Optional[Dict]:
        """Find the yoto-smart-stream project automatically."""
        projects = self.list_projects()
        for project in projects:
            project_details = self.get_project_services(project["id"])
            services = [edge["node"] for edge in project_details.get("services", {}).get("edges", [])]
            for service in services:
                if "yoto" in service["name"].lower():
                    return {
                        "project": project_details,
                        "service": service,
                        "all_services": services
                    }
        return None


def format_timestamp(timestamp: str) -> str:
    """Format ISO timestamp to readable format."""
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except:
        return timestamp


def cmd_list_projects(inspector: RailwayInspector, args):
    """List all Railway projects."""
    print("\n=== Railway Projects ===\n")
    projects = inspector.list_projects()
    
    if not projects:
        print("No projects found.")
        return
    
    for project in projects:
        print(f"Project: {project['name']}")
        print(f"  ID: {project['id']}")
        if project.get("description"):
            print(f"  Description: {project['description']}")
        print(f"  Created: {format_timestamp(project['createdAt'])}")
        print()


def cmd_list_services(inspector: RailwayInspector, args):
    """List services in a project."""
    if not args.project_id:
        print("Error: --project-id is required")
        sys.exit(1)
    
    print(f"\n=== Services in Project {args.project_id} ===\n")
    project = inspector.get_project_services(args.project_id)
    
    print(f"Project: {project.get('name', 'Unknown')}")
    print(f"\nServices:")
    services = [edge["node"] for edge in project.get("services", {}).get("edges", [])]
    
    if not services:
        print("  No services found.")
    else:
        for service in services:
            print(f"\n  Service: {service['name']}")
            print(f"    ID: {service['id']}")
            print(f"    Created: {format_timestamp(service['createdAt'])}")
    
    print(f"\nEnvironments:")
    environments = [edge["node"] for edge in project.get("environments", {}).get("edges", [])]
    
    if not environments:
        print("  No environments found.")
    else:
        for env in environments:
            print(f"\n  Environment: {env['name']}")
            print(f"    ID: {env['id']}")


def cmd_deployments(inspector: RailwayInspector, args):
    """List recent deployments."""
    if not args.project_id:
        print("Error: --project-id is required")
        sys.exit(1)
    
    environment_id = None
    if args.environment:
        # Get environment ID from name
        project = inspector.get_project_services(args.project_id)
        environments = [edge["node"] for edge in project.get("environments", {}).get("edges", [])]
        for env in environments:
            if env["name"] == args.environment:
                environment_id = env["id"]
                break
        
        if not environment_id:
            print(f"Error: Environment '{args.environment}' not found")
            sys.exit(1)
    
    print(f"\n=== Recent Deployments ===\n")
    deployments = inspector.get_deployments(
        args.project_id,
        environment_id=environment_id,
        service_id=args.service_id,
        limit=args.limit
    )
    
    if not deployments:
        print("No deployments found.")
        return
    
    for deployment in deployments:
        print(f"Deployment: {deployment['id']}")
        print(f"  Status: {deployment['status']}")
        print(f"  Created: {format_timestamp(deployment['createdAt'])}")
        if deployment.get("staticUrl"):
            print(f"  URL: https://{deployment['staticUrl']}")
        if deployment.get("meta"):
            print(f"  Meta: {json.dumps(deployment['meta'], indent=4)}")
        print()


def cmd_logs(inspector: RailwayInspector, args):
    """Get deployment logs."""
    if not args.deployment_id:
        print("Error: --deployment-id is required")
        sys.exit(1)
    
    print(f"\n=== Deployment Logs: {args.deployment_id} ===\n")
    logs = inspector.get_deployment_logs(args.deployment_id, limit=args.limit)
    
    if not logs:
        print("No logs found.")
        return
    
    for log in logs:
        timestamp = format_timestamp(log["timestamp"])
        severity = log.get("severity", "INFO")
        message = log["message"]
        
        if args.raw:
            print(message)
        else:
            print(f"[{timestamp}] [{severity}] {message}")


def cmd_health(inspector: RailwayInspector, args):
    """Check service health by examining recent deployments."""
    if not args.project_id or not args.service_id:
        print("Error: --project-id and --service-id are required")
        sys.exit(1)
    
    print(f"\n=== Service Health Check ===\n")
    
    # Get recent deployments
    deployments = inspector.get_deployments(
        args.project_id,
        service_id=args.service_id,
        limit=5
    )
    
    if not deployments:
        print("❌ No deployments found")
        return
    
    latest = deployments[0]
    print(f"Latest Deployment: {latest['id']}")
    print(f"  Status: {latest['status']}")
    print(f"  Created: {format_timestamp(latest['createdAt'])}")
    
    if latest.get("staticUrl"):
        url = f"https://{latest['staticUrl']}"
        print(f"  URL: {url}")
        
        # Try to check health endpoint
        try:
            response = requests.get(f"{url}/api/health", timeout=10)
            print(f"  Health Endpoint: {response.status_code}")
            if response.status_code == 200:
                print("  ✅ Service is healthy")
            else:
                print(f"  ⚠️ Service returned: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Health check failed: {e}")
    
    # Show recent deployment history
    print(f"\nRecent Deployment History:")
    for deployment in deployments:
        status_icon = "✅" if deployment["status"] == "SUCCESS" else "❌" if deployment["status"] == "FAILED" else "⏳"
        print(f"  {status_icon} {deployment['status']}: {format_timestamp(deployment['createdAt'])}")


def cmd_interactive(inspector: RailwayInspector, args):
    """Interactive mode - automatically finds and inspects yoto-smart-stream."""
    print("\n🔍 Finding yoto-smart-stream service...\n")
    
    result = inspector.find_yoto_project()
    if not result:
        print("❌ Could not find yoto-smart-stream service")
        return
    
    project = result["project"]
    service = result["service"]
    
    print(f"✅ Found service!")
    print(f"\nProject: {project['name']} ({project['id']})")
    print(f"Service: {service['name']} ({service['id']})")
    
    environments = [edge["node"] for edge in project.get("environments", {}).get("edges", [])]
    print(f"\nEnvironments:")
    for env in environments:
        print(f"  • {env['name']} ({env['id']})")
    
    # Get production deployments
    prod_env = next((e for e in environments if e["name"] == "production"), None)
    if prod_env:
        print(f"\n📦 Recent Production Deployments:")
        deployments = inspector.get_deployments(
            project["id"],
            environment_id=prod_env["id"],
            limit=3
        )
        
        for deployment in deployments:
            status_icon = "✅" if deployment["status"] == "SUCCESS" else "❌"
            print(f"  {status_icon} {deployment['status']}: {format_timestamp(deployment['createdAt'])}")
            if deployment.get("staticUrl"):
                print(f"     URL: https://{deployment['staticUrl']}")
        
        # Get logs from latest deployment
        if deployments:
            latest_id = deployments[0]["id"]
            print(f"\n📋 Recent Logs (latest 20 lines):")
            logs = inspector.get_deployment_logs(latest_id, limit=20)
            for log in logs[-20:]:  # Last 20 lines
                print(f"  {log['message']}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Railway Service Inspector - Direct GraphQL API access",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # list-projects
    subparsers.add_parser("list-projects", help="List all Railway projects")
    
    # list-services
    services_parser = subparsers.add_parser("list-services", help="List services in a project")
    services_parser.add_argument("--project-id", required=True, help="Project ID")
    
    # deployments
    deploy_parser = subparsers.add_parser("deployments", help="List recent deployments")
    deploy_parser.add_argument("--project-id", required=True, help="Project ID")
    deploy_parser.add_argument("--environment", help="Environment name (e.g., production)")
    deploy_parser.add_argument("--service-id", help="Service ID")
    deploy_parser.add_argument("--limit", type=int, default=10, help="Number of deployments (default: 10)")
    
    # logs
    logs_parser = subparsers.add_parser("logs", help="Get deployment logs")
    logs_parser.add_argument("--deployment-id", required=True, help="Deployment ID")
    logs_parser.add_argument("--limit", type=int, default=100, help="Number of log lines (default: 100)")
    logs_parser.add_argument("--raw", action="store_true", help="Raw log output (no timestamps)")
    
    # health
    health_parser = subparsers.add_parser("health", help="Check service health")
    health_parser.add_argument("--project-id", required=True, help="Project ID")
    health_parser.add_argument("--service-id", required=True, help="Service ID")
    
    # interactive
    subparsers.add_parser("interactive", help="Interactive mode (auto-finds yoto-smart-stream)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        inspector = RailwayInspector()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    try:
        if args.command == "list-projects":
            cmd_list_projects(inspector, args)
        elif args.command == "list-services":
            cmd_list_services(inspector, args)
        elif args.command == "deployments":
            cmd_deployments(inspector, args)
        elif args.command == "logs":
            cmd_logs(inspector, args)
        elif args.command == "health":
            cmd_health(inspector, args)
        elif args.command == "interactive":
            cmd_interactive(inspector, args)
        else:
            print(f"Unknown command: {args.command}")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
