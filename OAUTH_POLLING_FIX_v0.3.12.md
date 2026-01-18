# OAuth Polling Infinite Restart Fix

**Version**: v0.3.12+static-s3.2  
**Date**: 2026-01-18  
**Related**: Issue #82 (S3 Static Files Migration)

## Problem Summary

After migrating static files to S3 (Issue #82), OAuth authorization hung indefinitely at "Waiting for authorization..." with "Starting polling" message appearing repeatedly in console logs every ~10 seconds.

## Root Cause Analysis

The OAuth polling implementation used `setInterval` with conditional recursive calls to `startAuthPolling()`:

```javascript
// BROKEN CODE (v0.3.12+static-s3 through v0.3.12+static-s3.1)
authPollInterval = setInterval(async () => {
    pollCount++;
    // ... fetch /auth/poll ...
    
    if (pollCount > 1) {
        clearInterval(authPollInterval);
        pollCount = 0;  // ← RESETS COUNTER
        startAuthPolling();  // ← RECURSIVE CALL
        return;
    }
}, authPollDelay);
```

### The Infinite Loop

1. **First poll** (`pollCount=1`): Gets `pending`, check fails (`pollCount > 1` is false), continues
2. **Second poll** (`pollCount=2`): Gets `pending`, check passes (`pollCount > 1` is true)
3. **Restart triggered**: Clears interval, resets `pollCount` to 0, recursively calls `startAuthPolling()`
4. **Repeat**: New interval starts at step 1

This created a restart cycle every 2 poll attempts (~6 seconds), defeating the exponential backoff logic and preventing success detection.

## Solution

Replaced `setInterval` with `setTimeout` and self-rescheduling `poll()` function:

```javascript
// FIXED CODE (v0.3.12+static-s3.2)
const poll = async () => {
    try {
        const response = await fetch(`${API_BASE}/auth/poll`, ...);
        const data = await response.json();
        
        if (data.status === 'success') {
            // Handle success, DON'T reschedule
        } else if (data.status === 'expired') {
            // Handle expiration, DON'T reschedule
        } else {
            // Still pending - increase delay and continue
            const newDelay = Math.min(authPollDelay * 1.5, 8000);
            if (newDelay > authPollDelay) {
                authPollDelay = newDelay;
            }
            authPollInterval = setTimeout(poll, authPollDelay);  // ← RESCHEDULE SELF
        }
    } catch (error) {
        // Increase backoff on error and continue
        authPollDelay = Math.min(authPollDelay * 1.5, 8000);
        authPollInterval = setTimeout(poll, authPollDelay);
    }
};

// Start first poll
authPollInterval = setTimeout(poll, authPollDelay);
```

### Key Improvements

1. **No `pollCount` needed**: Delay increases on every `pending` response
2. **No recursive function calls**: `poll()` reschedules itself with `setTimeout`
3. **Proper exponential backoff**: 3s → 4.5s → 6.75s → 8s (max)
4. **Clean termination**: Success/expired stops rescheduling, no orphaned timers

## Files Modified

- `yoto_smart_stream/static/js/dashboard.js`: OAuth polling logic (lines 300-380)
- `yoto_smart_stream/__init__.py`: Version bump to v0.3.12+static-s3.2
- `yoto_smart_stream/static/*.html`: Cache-busting version updated to `?v=20260118-3`

## Deployment Notes

### S3 Bucket Deployment

Static files deployed to `s3://yoto-ui-dev-669589759577/`:
```bash
aws s3 sync yoto_smart_stream/static/ s3://yoto-ui-dev-669589759577/ \
  --exclude "*" --include "*.js" --include "*.html" --no-cli-pager
```

### Browser Caching Issue

Lambda serves static files with `Cache-Control: public, max-age=3600` (1 hour cache). After deployment:

1. **Hard refresh required**: Users must press Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
2. **Cache-busting parameter**: HTML files use `?v=20260118-3` to force reload
3. **Incognito mode**: Alternative for testing without cache

### Why Files Were Identical But Broken

Investigation revealed:
- S3 files were correctly uploaded and identical to source
- Lambda was correctly serving from S3
- OAuth `/auth/poll` endpoint was working (returning 200 OK)
- **The logic was broken**, not the file deployment!

## Testing Results

### Before Fix (v0.3.12+static-s3.1)

Console logs showed repeated restarts:
```
🔄 [OAuth] Starting polling for OAuth authorization (initial interval: 3 seconds)
[OAuth] Increasing poll interval from 3000ms to 4500ms (received pending status)
🔄 [OAuth] Starting polling for OAuth authorization (initial interval: 3 seconds)  ← RESTART
[OAuth] Increasing poll interval from 3000ms to 4500ms (received pending status)
🔄 [OAuth] Starting polling for OAuth authorization (initial interval: 3 seconds)  ← RESTART
```

UI stuck at "Waiting for authorization..." indefinitely.

### After Fix (v0.3.12+static-s3.2)

Expected console logs:
```
🔄 [OAuth] Starting polling for OAuth authorization (initial interval: 3 seconds)
[OAuth] Increasing poll interval from 3000ms to 4500ms (received pending status)
[OAuth] Increasing poll interval from 4500ms to 6750ms (received pending status)
🎉 [OAuth] OAuth Authentication Success! User authorized the application
✓ [OAuth] Tokens received and stored. Page reloading in 5 seconds...
```

## Lessons Learned

1. **Avoid `setInterval` for exponential backoff**: Use `setTimeout` with self-rescheduling
2. **`pollCount` is an anti-pattern**: State machines shouldn't need counters for backoff
3. **Recursive function calls are dangerous**: Easy to create infinite loops
4. **Browser caching defeats testing**: Always use hard refresh after JS changes
5. **Check the logic, not just the files**: Identical files can have broken implementations

## Related Issues

- **Issue #82**: Static files S3 migration (completed)
- **Issue #80**: Original OAuth implementation (completed, but introduced this bug in commit 7d6a825)

## Commit History

- `8aee941`: Fix OAuth polling with setTimeout (v0.3.12+static-s3.2) ✅
- `a89e03f`: First attempt with nested setInterval (v0.3.12+static-s3.1) ❌
- `4f69a74`: S3 static files migration (v0.3.12+static-s3)
- `7d6a825`: Introduced broken backoff logic (v0.3.11+oauth-fix.2)

## Verification Steps

To verify the fix is working:

1. Navigate to https://a34zdsc0vb.execute-api.us-east-1.amazonaws.com/
2. Press Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows) for hard refresh
3. Open browser console (F12)
4. Click "🔑 Connect Yoto Account"
5. Observe console logs:
   - Should see ONE "Starting polling" message
   - Should see gradual delay increases (3s → 4.5s → 6.75s)
   - Should NOT see repeated "Starting polling" messages
6. Complete authorization in Yoto app or web
7. Page should reload within 5 seconds after authorization

## Future Improvements

1. **Reduce cache duration**: Change `Cache-Control: max-age=3600` to `max-age=300` (5 minutes)
2. **Add ETag support**: Use S3 ETags for better cache invalidation
3. **Implement version in API response**: Return version from `/api/status` for verification
4. **Add polling health check**: Log warning if no status change after 10 polls
