# Transcription Settings Fix - Release 0.2.1

## Summary

Fixed critical issue where enabling transcription via Admin UI had no effect on the actual TranscriptionService instance. The service was only checking the Pydantic settings (which defaults to `False`), not the database settings.

## Problem

When a user toggled "Transcription Enabled" in the Admin UI, the setting was saved to the database but the TranscriptionService continued to check only the Pydantic default value (`False`). This meant:

1. User enables transcription in Admin UI → Setting saved to database
2. User attempts transcription → `get_transcription_service()` checks Pydantic settings (False) → Returns disabled error
3. Error message: `"Transcription disabled via configuration"`

Users saw conflicting UI (Settings shows ON) but service behavior (transcription fails).

## Solution

Updated `get_transcription_service()` in [yoto_smart_stream/core/transcription.py](yoto_smart_stream/core/transcription.py) to compute the effective `transcription_enabled` value with proper priority:

1. **Environment Variable** (highest priority): `TRANSCRIPTION_ENABLED` env var
2. **Database Setting**: Value from `Setting` table with key `"transcription_enabled"`
3. **Pydantic Default** (fallback): `settings.transcription_enabled` (default False)

### Key Changes

```python
def get_transcription_service() -> TranscriptionService:
    # Now reads from database Settings table instead of only Pydantic
    # Query: db.query(Setting).filter(Setting.key == "transcription_enabled")
    # Respects priority: env > DB > Pydantic default
```

## Testing

Created comprehensive test (`tmp/test_simple.py`) that verifies:

- ✓ Login to Admin UI works
- ✓ Get current transcription setting
- ✓ Enable transcription via API
- ✓ Transcription works when enabled
- ✓ Disable transcription via API  
- ✓ Transcription correctly blocked when disabled
- ✓ Re-enable transcription via API
- ✓ Transcription works again after re-enable

**Test Result**: ✓ PASSED

## Deployment

- **Commit**: `ce09afb` (Fix transcription: read effective setting from database in get_transcription_service)
- **Version**: Bumped to 0.2.1 (commit `5a5e71d`)
- **Deployed**: Railway develop environment
- **Health Check**: ✓ Service healthy, 10 audio files, v0.2.1

## Error Messages

The fix also ensures error messages correctly guide users:

**Before Fix**:
- `"Transcription disabled via configuration"` (misleading, vague)

**After Fix**:
- `"Transcription is disabled in Settings. Open Admin → System Settings to enable."` (clear, actionable)

## Benefits

1. Admin UI toggle now has immediate effect
2. No service restart required for setting changes
3. Clear error messages guide users to Settings
4. Proper priority system: env override > DB > default
5. Fallback handling if database unavailable

## Files Changed

- [yoto_smart_stream/core/transcription.py](yoto_smart_stream/core/transcription.py) - Fixed `get_transcription_service()` 
- [pyproject.toml](pyproject.toml) - Version bumped to 0.2.1
- Skills documentation updated (see below)

## Skills Documentation Updated

### Service Operations Guide
- Updated "Transcription Not Working" section
- Documents new Settings-based enablement flow
- Includes User Experience walkthrough
- Documents environment variable override mechanism
- Added priority order documentation

### API Reference
- Added new "Audio Transcription" API section
- Documented effective setting computation
- Added user experience flow
- Documented model selection options
- Included error response examples

## Verification Commands

```bash
# Check service is running
curl https://yoto-smart-stream-develop.up.railway.app/api/health | jq .

# Run integration test
python3 tmp/test_simple.py

# Expected: ✓ ALL TESTS PASSED
```
