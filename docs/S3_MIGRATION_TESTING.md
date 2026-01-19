# Railway Bucket Testing Guide

Complete guide for testing S3-compatible Railway Bucket storage after provisioning.

## Prerequisites

- Railway Bucket provisioned in target environment via Railway dashboard
- Service deployed and running
- Authentication credentials available

## Step 1: Provision Railway Bucket (Manual)

**Via Railway Dashboard:**
1. Navigate to Railway dashboard → Select project
2. Select target environment (PR, staging, or production)
3. Click "+" to add a service → Select "Bucket" (S3-compatible storage)
4. Railway automatically generates and sets environment variables:
   - `BUCKET` - Bucket name
   - `ACCESS_KEY_ID` - S3 access key
   - `SECRET_ACCESS_KEY` - S3 secret key
   - `ENDPOINT` - Storage endpoint URL (https://storage.railway.app)
   - `REGION` - Region (typically "auto")

## Step 2: Configure Storage Backend

Set the storage backend environment variable:

**Via Railway Dashboard:**
1. Navigate to environment → Variables
2. Add variable: `STORAGE_BACKEND=s3`
3. Service automatically restarts with S3 storage enabled

**Via Railway CLI (if linked):**
```bash
railway variables set STORAGE_BACKEND=s3 --environment <env-name>
```

**Verification:**
```bash
# Check logs confirm S3 initialization
railway logs --filter "Initialized S3Storage"
```

## Step 3: Run Migration Script (Dry Run)

Test the migration without actually moving files:

```bash
# Via Railway CLI (run in service context)
railway run python scripts/migrate_audio_to_s3.py --dry-run

# Or SSH into service
railway ssh
python scripts/migrate_audio_to_s3.py --dry-run
exit
```

**Expected Output:**
```
============================================================
AUDIO FILE MIGRATION: Volume → S3 Bucket
============================================================
Environment: pr-123
Source: /data/audio_files
Destination: s3://bucket-name
Endpoint: https://storage.railway.app
Dry Run: True
============================================================

Found 5 audio file(s) to migrate

Processing: story1.mp3 (2.45 MB)
  [DRY RUN] Would upload story1.mp3

...

============================================================
MIGRATION SUMMARY
============================================================
Total files: 5
Migrated: 5
Skipped (already migrated): 0
Failed: 0
============================================================

This was a dry run. No files were actually migrated.
Run without --dry-run to perform the migration.
```

## Step 4: Run Actual Migration

Migrate files to S3 storage:

```bash
# Migrate files
railway run python scripts/migrate_audio_to_s3.py

# Expected output shows successful uploads with verification
```

**Expected Output:**
```
Processing: story1.mp3 (2.45 MB)
  ✓ Migrated successfully (verified size: 2566144 bytes)

...

============================================================
MIGRATION SUMMARY
============================================================
Total files: 5
Migrated: 5
Skipped (already migrated): 0
Failed: 0
============================================================

✓ Migration completed successfully!

Local files remain in: /data/audio_files
You can delete them manually after verifying S3 storage works correctly.
Or re-run with --delete-after to automatically delete local files.
```

## Step 5: Test Audio Operations

### 5.1 Setup Environment Variables

```bash
# Set deployment URL
export DEPLOY_URL="https://yoto-smart-stream-pr-123.up.railway.app"

# Set credentials (should be in environment)
export SERVICE_USERNAME="<your-username>"
export SERVICE_PASSWORD="<your-password>"
```

### 5.2 Authenticate

```bash
# Login and get token
curl -X POST "$DEPLOY_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$SERVICE_USERNAME\",\"password\":\"$SERVICE_PASSWORD\"}" \
  -c cookies.txt \
  -v

# Extract token (adjust based on response format)
export TOKEN=$(cat cookies.txt | grep access_token | awk '{print $7}')
```

### 5.3 Test Audio Listing

```bash
# List all audio files
curl -X GET "$DEPLOY_URL/api/audio/list" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq

# Expected: JSON with files array including migrated files
```

**Expected Response:**
```json
{
  "files": [
    {
      "filename": "story1.mp3",
      "size": 2566144,
      "duration": 125,
      "url": "/api/audio/story1.mp3",
      "is_static": false,
      "transcript": {
        "status": "pending",
        "has_transcript": false
      }
    }
  ],
  "count": 5
}
```

### 5.4 Test Audio Download (Presigned URL)

```bash
# Request audio file - should get 307 redirect
curl -X GET "$DEPLOY_URL/api/audio/story1.mp3" \
  -H "Authorization: Bearer $TOKEN" \
  -L \
  -w "\nHTTP Status: %{http_code}\nRedirect URL: %{redirect_url}\n" \
  -o test-download.mp3

# Verify file downloaded
ls -lh test-download.mp3

# Should see:
# - HTTP Status: 200 (after 307 redirect)
# - Redirect URL: https://storage.railway.app/...?X-Amz-Algorithm=...
# - File size matches original
```

### 5.5 Test Audio Upload (New File to S3)

```bash
# Create test audio file
echo "Test audio for S3" > test-s3.txt
# In real scenario, use actual MP3 file

# Upload
curl -X POST "$DEPLOY_URL/api/audio/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test-s3.txt" \
  -F "filename=test-s3-upload" \
  -F "description=Testing S3 storage" | jq

# Expected: success response with filename
```

**Expected Response:**
```json
{
  "success": true,
  "filename": "test-s3-upload.mp3",
  "size": 18,
  "duration": 0,
  "description": "Testing S3 storage",
  "url": "/api/audio/test-s3-upload.mp3",
  "message": "Successfully uploaded 'test-s3-upload.mp3'",
  "transcript_status": "disabled"
}
```

### 5.6 Test TTS Generation (Direct to S3)

```bash
# Generate TTS audio
curl -X POST "$DEPLOY_URL/api/audio/generate-tts" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "test-tts-s3",
    "text": "Testing text to speech with S3 storage backend"
  }' | jq

# Expected: success with filename
```

**Expected Response:**
```json
{
  "success": true,
  "filename": "test-tts-s3.mp3",
  "size": 12345,
  "duration": 5,
  "url": "/api/audio/test-tts-s3.mp3",
  "message": "Successfully generated 'test-tts-s3.mp3'",
  "transcript_status": "completed"
}
```

### 5.7 Verify TTS File Accessible

```bash
# Download TTS file via presigned URL
curl -X GET "$DEPLOY_URL/api/audio/test-tts-s3.mp3" \
  -H "Authorization: Bearer $TOKEN" \
  -L -I

# Should show:
# HTTP/1.1 307 Temporary Redirect
# Location: https://storage.railway.app/...presigned-url...
# Then: HTTP/1.1 200 OK
```

## Step 6: Verify in Railway Dashboard

**Check Bucket Usage:**
1. Navigate to Railway dashboard → Environment → Bucket service
2. Verify:
   - Storage usage shows uploaded files
   - Metrics show successful operations
   - No errors in bucket logs

**Check Application Logs:**
```bash
# Filter for S3-related logs
railway logs --filter "S3Storage"

# Check for errors
railway logs --filter "@level:error"

# Expected: Initialization messages, no errors
```

## Verification Checklist

- [ ] Railway Bucket provisioned in environment
- [ ] `STORAGE_BACKEND=s3` environment variable set
- [ ] Service restarted and initialized S3Storage
- [ ] Migration script dry-run completed successfully
- [ ] Actual migration completed (all files uploaded)
- [ ] Audio listing returns all files (migrated + new)
- [ ] Audio download returns 307 redirect to presigned URL
- [ ] Presigned URLs work (files download successfully)
- [ ] New audio upload saves to S3
- [ ] TTS generation saves to S3
- [ ] No errors in application logs
- [ ] Bucket metrics show usage in Railway dashboard

## Rollback Procedure

If issues occur, revert to local storage:

```bash
# Via Railway Dashboard: Set STORAGE_BACKEND=local
# Or via CLI:
railway variables set STORAGE_BACKEND=local --environment <env-name>

# Service restarts automatically
# Files remain in both locations (safe - no data loss)
```

## Cleanup (Optional)

After successful migration and verification:

```bash
# Delete local files to free volume space
railway run python scripts/migrate_audio_to_s3.py --delete-after

# Warning: Only do this after confirming:
# 1. All files accessible via S3
# 2. Downloads work correctly
# 3. Presigned URLs function properly
```

## Cost Verification

**Expected Costs:**
- **Bucket Storage**: ~$0.015/GB-month
- **Bucket Egress**: $0 (presigned URLs bypass egress charges)
- **Volume Storage** (after cleanup): Reduced by audio file size

**Savings Calculation:**
- Previous: $0.25/GB-month (volume)
- New: $0.015/GB-month (bucket)
- **Savings: 94%**

**Check in Railway Dashboard:**
1. Navigate to project → Usage
2. Compare before/after:
   - Volume usage (should decrease after cleanup)
   - Bucket usage (should show audio files)
   - Total storage costs (should be significantly lower)

## Troubleshooting

### Migration Script Fails

**Error:** "STORAGE_BACKEND must be set to 's3'"
- **Solution:** Set environment variable in Railway dashboard

**Error:** "BUCKET environment variable not set"
- **Solution:** Ensure Railway Bucket is provisioned and variables are set

### Presigned URLs Don't Work

**Symptom:** 403 Forbidden or signature errors
- **Check:** Bucket credentials are correct
- **Check:** Clock sync (presigned URLs are time-sensitive)
- **Solution:** Regenerate bucket or check ENDPOINT/REGION settings

### Files Not Found After Migration

**Symptom:** 404 errors when accessing files
- **Check:** Migration script summary (any failures?)
- **Check:** Bucket contents via Railway dashboard
- **Solution:** Re-run migration script (it skips existing files)

### High Egress Costs

**Symptom:** Unexpected egress charges on bucket
- **Check:** Audio endpoint returns 307 redirects (not proxying)
- **Check:** Application logs for direct S3 reads
- **Solution:** Ensure `storage_backend == "s3"` branch uses presigned URLs

## Additional Resources

- **Migration Script**: `scripts/migrate_audio_to_s3.py`
- **Storage Abstraction**: `yoto_smart_stream/storage/`
- **Configuration**: `yoto_smart_stream/config.py`
- **Railway Buckets Docs**: https://docs.railway.app/reference/volumes#buckets
- **Issue Tracker**: GitHub Issues #85
