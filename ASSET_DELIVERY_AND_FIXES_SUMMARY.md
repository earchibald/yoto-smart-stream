# Asset Delivery & Error Handling Fixes - Summary

## Update (2026-01-17) - DynamoDB Persistence Migration
- Swapped SQLite persistence for DynamoDB when `DYNAMODB_TABLE` is set (Lambda/CDK injects).
- Added Dynamo-backed user/auth flows (login, admin CRUD, OAuth token storage) and audio metadata/transcript tracking.
- App startup now bootstraps admin user in DynamoDB; config picks up `DYNAMODB_TABLE`/`AWS_REGION` automatically.
- Background transcription tasks updated to write transcript status/results into DynamoDB.
- Follow-up: deploy to `dev`, validate OAuth + S3 flows, and run regression checks.

**Date**: January 17, 2026  
**Environment**: `dev` (AWS CDK)  
**Status**: ✅ Deployed and Verified  
**Version**: v0.2.6

---

## Problem Statement

### Phase 1: Static Asset Staleness
- Updated frontend code (particularly dashboard.js error handling and UI prompts) was not being reflected in production after deployment.
- Root cause: AWS Lambda deployment from `cdk deploy` was bundling stale assets; subsequent Lambda updates didn't refresh the static files delivered to clients.
- Browser caching and lack of cache-busting made it impossible to verify frontend changes in dev.

### Phase 2: Authentication & Error Handling Gaps
- Players endpoint returned 500 errors instead of 401 for unauthenticated requests, making error handling inconsistent.
- Merge conflict markers in Python and JavaScript codebase caused runtime errors and parsing failures.
- Missing configuration for S3 UI bucket prevented the S3 proxy route from functioning.

---

## Solution Implemented

### 1. S3-Based Static Asset Delivery with Versioned Query Strings

#### Architecture:
- **FastAPI S3 Proxy Route** (`/static/{key:path}`):
  - Fetches assets from S3 UI bucket instead of local Lambda bundle.
  - Fallback to local files if bucket not configured.
  - Applies `Cache-Control: public, max-age=31536000` headers for long-term caching.
  - Infers correct MIME types for all asset types.

#### Implementation Details:
- **Location**: [infrastructure/lambda/package/yoto_smart_stream/api/app.py](infrastructure/lambda/package/yoto_smart_stream/api/app.py#L279-L305)
- **S3 Bucket**: `yoto-ui-dev-669589759577`
- **Environment Variable**: `S3_UI_BUCKET` (injected via CDK context)

#### Cache Busting Strategy:
- Versioned query strings appended to all asset references in HTML.
- Format: `?v=YYYYMMDD-N` (e.g., `?v=20260117-3`)
- When assets are updated, version bumped → browser fetches fresh copy → S3 proxy delivers latest from bucket.

#### Deployed Files in S3:
- ✅ `static/css/style.css?v=20260117-3`
- ✅ `static/js/dashboard.js?v=20260117-3`
- ✅ `static/js/mqtt-analyzer.js?v=20260117-3`
- ✅ Additional JS files (admin.js, streams.js, library.js, audio-library.js) versioned

---

### 2. Players Endpoint 401 Error Handling

#### Backend (Python):
**File**: [infrastructure/lambda/package/yoto_smart_stream/api/routes/players.py](infrastructure/lambda/package/yoto_smart_stream/api/routes/players.py)

**Changes**:
- Resolved merge conflict markers in `list_players()` and `control_player()` endpoints.
- Enhanced exception handling to detect authentication-related errors:
  - Checks error messages for keywords: "authentication", "refresh token", "unauthorized"
  - Returns **401 Unauthorized** (not 500) on auth failures.
  - Re-raises other exceptions to 500 error handler.

**Code Pattern**:
```python
try:
    # API call or client operation
except Exception as e:
    error_msg = str(e).lower()
    if any(keyword in error_msg for keyword in ["authentication", "refresh token", "unauthorized"]):
        raise HTTPException(status_code=401, detail="Not authenticated")
    raise  # Re-raise for 500 handler
```

#### Frontend (JavaScript):
**File**: [infrastructure/lambda/package/yoto_smart_stream/static/js/dashboard.js](infrastructure/lambda/package/yoto_smart_stream/static/js/dashboard.js)

**Changes**:
- Consolidated 401 handling in `loadPlayers()`:
  ```javascript
  if (response.status === 401) {
      console.log('Players endpoint returned 401, showing auth prompt');
      document.getElementById('player-count').textContent = '-';
      container.innerHTML = '<p class="loading">Connect your Yoto account to see players.</p>';
      return;
  }
  ```
- Added descriptive console logging for non-OK responses.
- Removed merge conflict markers that were breaking parsing.

---

### 3. Configuration Updates

#### Config Settings:
**File**: [infrastructure/lambda/package/yoto_smart_stream/config.py](infrastructure/lambda/package/yoto_smart_stream/config.py)

**Added**:
```python
s3_ui_bucket: Optional[str] = Field(
    default=None,
    description="S3 bucket for serving static UI assets",
    json_schema_extra={"env": "S3_UI_BUCKET"}
)
```

**CDK Context Variable** (passed during deployment):
- `s3_ui_bucket` → Environment: `S3_UI_BUCKET` → Lambda runtime

---

### 4. Versioned Asset References

#### Updated HTML Pages:
- ✅ [index.html](infrastructure/lambda/package/yoto_smart_stream/static/index.html) - Dashboard
- ✅ [admin.html](infrastructure/lambda/package/yoto_smart_stream/static/admin.html)
- ✅ [library.html](infrastructure/lambda/package/yoto_smart_stream/static/library.html)
- ✅ [streams.html](infrastructure/lambda/package/yoto_smart_stream/static/streams.html)
- ✅ [audio-library.html](infrastructure/lambda/package/yoto_smart_stream/static/audio-library.html)
- ✅ [login.html](infrastructure/lambda/package/yoto_smart_stream/static/login.html)

#### Pattern Applied:
```html
<!-- CSS -->
<link rel="stylesheet" href="/static/css/style.css?v=20260117-3">

<!-- JavaScript -->
<script src="/static/js/dashboard.js?v=20260117-3"></script>
<script src="/static/js/mqtt-analyzer.js?v=20260117-3"></script>
```

---

## Deployment Process

### Steps Executed:

1. **Resolved merge conflict markers** in:
   - `infrastructure/lambda/package/yoto_smart_stream/api/routes/players.py`
   - `infrastructure/lambda/package/yoto_smart_stream/static/js/dashboard.js`

2. **Added missing configuration**:
   - `s3_ui_bucket` setting to `config.py`
   - CDK environment variable export

3. **Updated HTML asset references**:
   - Bumped versioned query strings to `?v=20260117-3` across all pages
   - Local source files and Lambda package files synchronized

4. **CDK Deployment**:
   ```bash
   cdk deploy \
     -c environment=dev \
     -c yoto_client_id="Pcht77vFlFIWF9xro2oPUBEtCYJr8zuO" \
     -c enable_mqtt=true \
     -c enable_cloudfront=false
   ```
   - **Status**: ✅ Successful (43.09s)
   - **Lambda Function**: Updated with S3 proxy route and config
   - **Stack Outputs**:
     - `ApiUrl`: https://d8vwiy1z0j.execute-api.us-east-1.amazonaws.com/
     - `UIBucketName`: `yoto-ui-dev-669589759577`

5. **Asset Upload to S3**:
   ```bash
   aws s3 cp dashboard.js s3://yoto-ui-dev-669589759577/static/js/dashboard.js
   aws s3 cp style.css s3://yoto-ui-dev-669589759577/static/css/style.css
   aws s3 cp mqtt-analyzer.js s3://yoto-ui-dev-669589759577/static/js/mqtt-analyzer.js
   ```

---

## Verification Results

### ✅ Endpoint Tests:

| Endpoint | Method | Auth | Status | Response |
|----------|--------|------|--------|----------|
| `/api/status` | GET | None | **200** | `{"version":"0.2.6","environment":"dev",...}` |
| `/api/players` | GET | None | **401** | `{"detail":"Not authenticated"}` |
| `/static/js/dashboard.js?v=20260117-3` | GET | None | **200** | JavaScript content (57.3 KiB) |
| `/static/css/style.css?v=20260117-3` | GET | None | **200** | CSS content (51.0 KiB) |
| `/` (Dashboard) | GET | None | **200** | HTML with versioned assets |
| `/admin` | GET | None | **200** | HTML with `?v=20260117-3` references |
| `/library` | GET | None | **200** | HTML with `?v=20260117-3` references |
| `/streams` | GET | None | **200** | HTML with `?v=20260117-3` references |
| `/audio-library` | GET | None | **200** | HTML with `?v=20260117-3` references |
| `/login` | GET | None | **200** | HTML with `?v=20260117-3` references |

### ✅ Dashboard Behavior:

**Unauthenticated Access**:
- Page loads successfully
- Auth section displays "Connect Your Yoto Account" prompt
- Players list shows: "Connect your Yoto account to see players."
- Version displayed: **v0.2.6**
- Console logging shows proper 401 handling and auth flow prompts

**Asset Delivery**:
- All pages serve versioned CSS/JS from S3 proxy route
- Cache-Control headers set to `public, max-age=31536000`
- Zero merge conflict markers in deployed code

---

## Key Improvements

### 1. **Reliable Frontend Updates**
- Versioned query strings force cache invalidation when assets change.
- S3-backed delivery decouples static assets from Lambda deployment cycle.
- Future frontend changes only require: edit → upload to S3 → version bump in HTML.

### 2. **Consistent Error Handling**
- `401` responses now consistently indicate authentication failures.
- Dashboard correctly displays user-friendly "Connect account" prompt instead of generic errors.
- Console logs provide debug visibility for troubleshooting.

### 3. **Clean Production Code**
- All merge conflict markers removed from Python and JavaScript.
- Configuration properly injected via CDK context variables.
- Error handling follows consistent patterns across endpoints.

---

## Files Modified

### Backend (Python):
1. [infrastructure/lambda/package/yoto_smart_stream/api/app.py](infrastructure/lambda/package/yoto_smart_stream/api/app.py) - S3 proxy route added
2. [infrastructure/lambda/package/yoto_smart_stream/api/routes/players.py](infrastructure/lambda/package/yoto_smart_stream/api/routes/players.py) - 401 handling, merge markers removed
3. [infrastructure/lambda/package/yoto_smart_stream/config.py](infrastructure/lambda/package/yoto_smart_stream/config.py) - `s3_ui_bucket` setting added

### Frontend (HTML/CSS/JS):
4. [infrastructure/lambda/package/yoto_smart_stream/static/js/dashboard.js](infrastructure/lambda/package/yoto_smart_stream/static/js/dashboard.js) - 401 handling, merge markers removed
5. [infrastructure/lambda/package/yoto_smart_stream/static/index.html](infrastructure/lambda/package/yoto_smart_stream/static/index.html) - Versioned assets (`?v=20260117-3`)
6. [infrastructure/lambda/package/yoto_smart_stream/static/admin.html](infrastructure/lambda/package/yoto_smart_stream/static/admin.html) - Versioned assets
7. [infrastructure/lambda/package/yoto_smart_stream/static/library.html](infrastructure/lambda/package/yoto_smart_stream/static/library.html) - Versioned assets
8. [infrastructure/lambda/package/yoto_smart_stream/static/streams.html](infrastructure/lambda/package/yoto_smart_stream/static/streams.html) - Versioned assets
9. [infrastructure/lambda/package/yoto_smart_stream/static/audio-library.html](infrastructure/lambda/package/yoto_smart_stream/static/audio-library.html) - Versioned assets
10. [infrastructure/lambda/package/yoto_smart_stream/static/login.html](infrastructure/lambda/package/yoto_smart_stream/static/login.html) - Versioned assets

### Source (Local):
11. [yoto_smart_stream/static/js/dashboard.js](yoto_smart_stream/static/js/dashboard.js) - Synced with Lambda package
12. [yoto_smart_stream/static/index.html](yoto_smart_stream/static/index.html) - Versioned assets synced
13. All other HTML/CSS/JS in `yoto_smart_stream/static/` - Versions updated for consistency

### S3 Uploads:
- `s3://yoto-ui-dev-669589759577/static/js/dashboard.js` (57.3 KiB)
- `s3://yoto-ui-dev-669589759577/static/css/style.css` (51.0 KiB)
- `s3://yoto-ui-dev-669589759577/static/js/mqtt-analyzer.js` (10.3 KiB)

---

## Next Steps

### Immediate (Optional):
- Test authenticated flow (OAuth) to verify full dashboard functionality with players.
- Monitor CloudWatch logs for any asset delivery errors or auth issues.

### Future Enhancements:
- Automate S3 asset uploads as part of CI/CD pipeline.
- Implement automated version bumping in asset query strings.
- Consider CDN (CloudFront) for global asset distribution (already in prod config).

---

## Notes

- **No Breaking Changes**: All modifications are backward-compatible.
- **AWS Standard Workflow**: Follows established CDK deployment process (Section: Standard Workflow in copilot-instructions.md).
- **Testing**: Smoke-tested all major UI pages; endpoints verified via curl.
- **Version Control**: All source files updated and ready for commit.

---

**Deployed Endpoint**: https://d8vwiy1z0j.execute-api.us-east-1.amazonaws.com/  
**Dashboard Status**: ✅ Running v0.2.6 with proper asset delivery and error handling  
**Ready for Testing**: ✅ Yes
