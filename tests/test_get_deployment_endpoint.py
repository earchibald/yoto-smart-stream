#!/usr/bin/env python3
"""
Tests for get_deployment_endpoint.py script

This module tests the Railway deployment endpoint retrieval functionality.
"""

import os
import sys

import pytest

# Add parent directory to path to import the script
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        "..",
        ".github",
        "skills",
        "railway-service-management",
        "scripts",
    ),
)
from get_deployment_endpoint import RailwayDeploymentInfo  # noqa: E402


class TestRailwayDeploymentInfo:
    """Test the RailwayDeploymentInfo class."""

    def test_extract_endpoint_url_from_simple_domain(self):
        """Test extracting URL from a simple domain field."""
        client = RailwayDeploymentInfo.__new__(RailwayDeploymentInfo)

        data = {"domain": "example.up.railway.app"}

        url = client.extract_endpoint_url(data)
        assert url == "https://example.up.railway.app"

    def test_extract_endpoint_url_from_domains_object(self):
        """Test extracting URL from Railway status domains object."""
        client = RailwayDeploymentInfo.__new__(RailwayDeploymentInfo)

        data = {
            "domains": {
                "serviceDomains": [{"domain": "yoto-smart-stream-production.up.railway.app"}],
                "customDomains": [],
            }
        }

        url = client.extract_endpoint_url(data)
        assert url == "https://yoto-smart-stream-production.up.railway.app"

    def test_extract_endpoint_url_from_status_structure(self):
        """Test extracting URL from full Railway status response structure."""
        client = RailwayDeploymentInfo.__new__(RailwayDeploymentInfo)

        data = {
            "environments": {
                "edges": [
                    {
                        "node": {
                            "name": "production",
                            "serviceInstances": {
                                "edges": [
                                    {
                                        "node": {
                                            "serviceName": "yoto-smart-stream",
                                            "domains": {
                                                "serviceDomains": [
                                                    {
                                                        "domain": "yoto-smart-stream-production.up.railway.app"
                                                    }
                                                ],
                                                "customDomains": [],
                                            },
                                        }
                                    }
                                ]
                            },
                        }
                    }
                ]
            }
        }

        url = client.extract_endpoint_url(data)
        assert url == "https://yoto-smart-stream-production.up.railway.app"

    def test_extract_endpoint_url_with_url_field(self):
        """Test extracting URL from direct url field."""
        client = RailwayDeploymentInfo.__new__(RailwayDeploymentInfo)

        data = {"url": "example.up.railway.app"}

        url = client.extract_endpoint_url(data)
        assert url == "https://example.up.railway.app"

    def test_extract_endpoint_url_with_https(self):
        """Test that URLs with https:// prefix are preserved."""
        client = RailwayDeploymentInfo.__new__(RailwayDeploymentInfo)

        data = {"url": "https://example.up.railway.app"}

        url = client.extract_endpoint_url(data)
        assert url == "https://example.up.railway.app"

    def test_extract_endpoint_url_returns_none_when_not_found(self):
        """Test that None is returned when no URL is found."""
        client = RailwayDeploymentInfo.__new__(RailwayDeploymentInfo)

        data = {"id": "some-id", "status": "SUCCESS"}

        url = client.extract_endpoint_url(data)
        assert url is None

    def test_extract_endpoint_url_empty_domains(self):
        """Test that None is returned when domains array is empty."""
        client = RailwayDeploymentInfo.__new__(RailwayDeploymentInfo)

        data = {"domains": {"serviceDomains": [], "customDomains": []}}

        url = client.extract_endpoint_url(data)
        assert url is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
