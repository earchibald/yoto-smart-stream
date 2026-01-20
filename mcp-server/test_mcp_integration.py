"""
Integration tests for all MCP server tools.

Tests verify that each of the 7 structured query tools:
1. Accept correct input parameters
2. Return properly formatted JSON responses
3. Handle edge cases appropriately
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from server import (
    LibraryStatsInput,
    ListCardsInput,
    SearchCardsInput,
    ListPlaylistsInput,
    GetMetadataKeysInput,
    GetFieldValuesInput,
    OAuthInput,
)


# Mock library data for testing
MOCK_LIBRARY_DATA = {
    "cards": [
        {
            "id": "card-1",
            "title": "Math Basics",
            "author": "Teacher A",
            "type": "interactive",
            "description": "Learn basic arithmetic",
            "duration": 300,
        },
        {
            "id": "card-2",
            "title": "Math Algebra",
            "author": "Teacher B",
            "type": "story",
            "description": "Introduction to algebra",
            "duration": 450,
        },
        {
            "id": "card-3",
            "title": "Science Physics",
            "author": "Teacher C",
            "type": "interactive",
            "description": "Physics fundamentals",
            "duration": 600,
        },
    ],
    "playlists": [
        {
            "id": "playlist-1",
            "name": "Math Series",
            "item_count": 2,
            "created_date": "2024-01-01",
        },
        {
            "id": "playlist-2",
            "name": "Science Basics",
            "item_count": 1,
            "created_date": "2024-01-15",
        },
    ],
}


class TestLibraryStatsInput:
    """Test LibraryStatsInput model validation."""

    def test_library_stats_input_valid(self):
        """Valid LibraryStatsInput should create successfully."""
        params = LibraryStatsInput(service_url="https://example.com")
        assert params.service_url == "https://example.com"

    def test_library_stats_input_optional_url(self):
        """service_url should be optional in LibraryStatsInput."""
        params = LibraryStatsInput()
        assert params.service_url is None


class TestListCardsInput:
    """Test ListCardsInput model validation."""

    def test_list_cards_input_valid(self):
        """Valid ListCardsInput should create successfully."""
        params = ListCardsInput(limit=50, service_url="https://example.com")
        assert params.limit == 50
        assert params.service_url == "https://example.com"

    def test_list_cards_input_default_limit(self):
        """Default limit should be 20."""
        params = ListCardsInput()
        assert params.limit == 20

    def test_list_cards_input_limit_constraints(self):
        """Limit should be between 1 and 100."""
        # Valid bounds
        assert ListCardsInput(limit=1).limit == 1
        assert ListCardsInput(limit=100).limit == 100

        # Invalid bounds should raise ValueError
        with pytest.raises(ValueError):
            ListCardsInput(limit=0)

        with pytest.raises(ValueError):
            ListCardsInput(limit=101)


class TestSearchCardsInput:
    """Test SearchCardsInput model validation."""

    def test_search_cards_input_valid(self):
        """Valid SearchCardsInput should create successfully."""
        params = SearchCardsInput(
            title_contains="math", limit=30, service_url="https://example.com"
        )
        assert params.title_contains == "math"
        assert params.limit == 30

    def test_search_cards_input_title_required(self):
        """title_contains should be required."""
        with pytest.raises(ValueError):
            SearchCardsInput()

    def test_search_cards_input_limit_constraints(self):
        """Limit should be between 1 and 100."""
        # Valid
        assert SearchCardsInput(title_contains="test", limit=1).limit == 1
        assert SearchCardsInput(title_contains="test", limit=100).limit == 100

        # Invalid
        with pytest.raises(ValueError):
            SearchCardsInput(title_contains="test", limit=101)


class TestGetFieldValuesInput:
    """Test GetFieldValuesInput model validation."""

    def test_get_field_values_input_valid(self):
        """Valid GetFieldValuesInput should create successfully."""
        params = GetFieldValuesInput(
            field_name="author", limit=50, service_url="https://example.com"
        )
        assert params.field_name == "author"
        assert params.limit == 50

    def test_get_field_values_input_field_required(self):
        """field_name should be required."""
        with pytest.raises(ValueError):
            GetFieldValuesInput()

    def test_get_field_values_input_limit_constraints(self):
        """Limit should be between 1 and 500."""
        # Valid bounds
        assert GetFieldValuesInput(field_name="test", limit=1).limit == 1
        assert GetFieldValuesInput(field_name="test", limit=500).limit == 500

        # Invalid bounds
        with pytest.raises(ValueError):
            GetFieldValuesInput(field_name="test", limit=501)


class TestToolResponses:
    """Test that tool responses are properly formatted JSON."""

    def test_library_stats_response_format(self):
        """library_stats should return dict with total_cards and total_playlists."""
        from server import get_library_stats

        result = get_library_stats(MOCK_LIBRARY_DATA)

        # Verify response structure
        assert isinstance(result, dict)
        assert "total_cards" in result
        assert "total_playlists" in result
        assert isinstance(result["total_cards"], int)
        assert isinstance(result["total_playlists"], int)

        # Verify counts match mock data
        assert result["total_cards"] == 3
        assert result["total_playlists"] == 2

    def test_list_cards_response_format(self):
        """list_cards should return list of card dicts with metadata."""
        from server import get_all_cards

        result = get_all_cards(MOCK_LIBRARY_DATA, limit=10)

        # Verify response structure
        assert isinstance(result, list)
        assert len(result) <= 10
        assert len(result) == 3  # All cards fit under limit

        # Verify card structure
        for card in result:
            assert isinstance(card, dict)
            assert "id" in card
            assert "title" in card
            assert "author" in card

    def test_search_cards_response_format(self):
        """search_cards should return list of matching cards."""
        from server import search_library

        result = search_library(MOCK_LIBRARY_DATA, "math", limit=10)

        # Verify response structure
        assert isinstance(result, list)
        assert len(result) >= 1

        # Should find math cards
        assert any("math" in card["title"].lower() for card in result)

    def test_list_playlists_response_format(self):
        """list_playlists should return list of playlist dicts."""
        from server import get_all_playlists

        result = get_all_playlists(MOCK_LIBRARY_DATA)

        # Verify response structure
        assert isinstance(result, list)
        assert len(result) == 2

        # Verify playlist structure
        for playlist in result:
            assert isinstance(playlist, dict)
            assert "id" in playlist
            assert "name" in playlist
            assert "item_count" in playlist

    def test_get_metadata_keys_response_format(self):
        """get_metadata_keys should return sorted list of field names."""
        from server import get_metadata_keys

        result = get_metadata_keys(MOCK_LIBRARY_DATA)

        # Verify response structure
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(key, str) for key in result)

        # Should include common card fields
        assert "id" in result
        assert "title" in result

        # Should be sorted
        assert result == sorted(result)

    def test_get_field_values_response_format(self):
        """get_field_values should return sorted list of unique values for a field."""
        from server import get_field_values

        result = get_field_values(MOCK_LIBRARY_DATA, "author", limit=10)

        # Verify response structure
        assert isinstance(result, list)
        assert len(result) >= 1
        assert all(isinstance(value, str) for value in result)

        # Should include teachers from mock data
        assert "Teacher A" in result
        assert "Teacher B" in result

        # Should be sorted
        assert result == sorted(result)


class TestToolEdgeCases:
    """Test edge cases and error handling."""

    def test_search_with_no_matches(self):
        """search_library should return empty list when no cards match."""
        from server import search_library

        result = search_library(MOCK_LIBRARY_DATA, "nonexistent", limit=10)
        assert result == []

    def test_list_cards_respects_limit(self):
        """list_cards should respect the limit parameter."""
        from server import get_all_cards

        result_5 = get_all_cards(MOCK_LIBRARY_DATA, limit=2)
        assert len(result_5) <= 2

        result_all = get_all_cards(MOCK_LIBRARY_DATA, limit=100)
        assert len(result_all) == 3

    def test_get_field_values_with_nonexistent_field(self):
        """get_field_values should return empty list for nonexistent field."""
        from server import get_field_values

        result = get_field_values(MOCK_LIBRARY_DATA, "nonexistent_field", limit=10)
        assert result == []

    def test_get_metadata_keys_includes_all_fields(self):
        """get_metadata_keys should include all fields used in any card."""
        from server import get_metadata_keys

        result = get_metadata_keys(MOCK_LIBRARY_DATA)

        # Should include all fields from cards
        expected_fields = {"id", "title", "author", "type", "description", "duration"}
        for field in expected_fields:
            assert field in result, f"Missing field: {field}"

    def test_get_field_values_handles_lists(self):
        """get_field_values should handle fields with list values."""
        library_data = {
            "cards": [
                {
                    "id": "card-1",
                    "tags": ["math", "geometry"],
                },
                {
                    "id": "card-2",
                    "tags": ["science", "physics"],
                },
            ],
            "playlists": [],
        }

        from server import get_field_values

        result = get_field_values(library_data, "tags", limit=10)

        # Should flatten lists
        assert "math" in result
        assert "geometry" in result
        assert "science" in result
        assert "physics" in result


class TestInputValidation:
    """Test that input validation prevents invalid parameters."""

    def test_list_cards_limit_type_validation(self):
        """ListCardsInput should validate that limit is an integer."""
        with pytest.raises((ValueError, TypeError)):
            ListCardsInput(limit="not-an-int")

    def test_search_cards_empty_title(self):
        """SearchCardsInput should require at least 1 character in title_contains."""
        # Empty string should fail validation
        with pytest.raises(ValueError):
            SearchCardsInput(title_contains="")

        # Single character should be valid
        params = SearchCardsInput(title_contains="a")
        assert params.title_contains == "a"

    def test_get_field_values_special_characters(self):
        """GetFieldValuesInput should handle field names with special characters."""
        params = GetFieldValuesInput(field_name="field_with_underscore")
        assert params.field_name == "field_with_underscore"

        params2 = GetFieldValuesInput(field_name="field-with-dash")
        assert params2.field_name == "field-with-dash"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
