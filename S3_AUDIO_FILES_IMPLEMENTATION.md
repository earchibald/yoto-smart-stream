# S3 Audio Files Implementation Report

## Overview

The S3 audio_files implementation is **complete and tested** in the Yoto Smart Stream application. Audio files are stored in AWS S3 and streamed efficiently to Yoto devices via Lambda-based API endpoints.

## Architecture

### Storage
- **S3 Bucket**: `yoto-audio-{environment}-{account_id}`
  - Example: `yoto-audio-dev-669589759577`
- **Versioning**: Enabled in production, disabled in development
- **CORS**: Configured for cross-origin audio streaming
- **Lifecycle**: Automatic cleanup of old versions (30 days) in production
- **Removal Policy**: Retained in production, auto-deleted in development

### Lambda Integration
- **Environment Variable**: `S3_AUDIO_BUCKET` set automatically by CDK
- **IAM Permissions**: 
  - `s3:GetObject` - Read audio files
  - `s3:ListBucket` - List audio files
  - `s3:PutObject` - Upload audio files
- **Lambda Extension**: AWS Parameters & Secrets extension for token caching (1000ms TTL)

### API Endpoints

#### 1. List Audio Files
```
GET /audio/list
```
Returns list of all audio files with metadata (size, duration, transcript status)
- **With S3**: Lists objects from S3 bucket
- **Local Fallback**: Lists files from `audio_files/` directory

#### 2. Stream Single Audio File
```
GET /audio/{filename}
```
Streams a single audio file with byte-range support for seeking
- **With S3**: Streams from S3 using Lambda Extension HTTP caching
- **Local Fallback**: Serves from local filesystem
- **Headers**: `Accept-Ranges: bytes`, `Cache-Control: public, max-age=3600`

#### 3. Upload Audio File
```
POST /audio/upload
```
Upload new audio file to S3 (or local directory)
- **With S3**: Saves to S3 bucket
- **Local Fallback**: Saves to `audio_files/` directory

#### 4. Stream Queue as Continuous Audio
```
GET /streams/{stream_name}/stream.mp3
```
Streams audio queue as single continuous MP3 file
- **With S3**: Concatenates files from S3
- **Local Fallback**: Concatenates files from local directory
- **Play Modes**: Sequential, Loop, Shuffle, Endless-Shuffle

#### 5. Generate TTS Audio
```
POST /audio/generate-tts
```
Generate text-to-speech audio using AWS Polly and save to S3

#### 6. Audio Search
```
GET /audio/search?query=story
```
Search for audio files by name

### Code Implementation

#### S3 Utilities (`yoto_smart_stream/utils/s3.py`)
```python
def s3_enabled() -> bool
    """Check if S3 is available (Lambda + bucket configured)"""

def object_exists(bucket: str, key: str) -> bool
    """Check if S3 object exists"""

def stream_object(bucket: str, key: str, chunk_size: int) -> Generator
    """Stream object from S3 in chunks"""

def upload_file(bucket: str, key: str, source_path: str) -> Optional[str]
    """Upload file to S3 and return URL"""
```

#### Stream Generation (`yoto_smart_stream/api/routes/streams.py`)
```python
async def generate_sequential_stream(
    queue_files: List[str], 
    audio_files_dir, 
    play_mode: str
) -> AsyncGenerator[bytes, None]
    """
    Generate stream by reading files from S3 or local directory.
    Yields audio chunks for streaming response.
    
    Play modes:
    - sequential: Play once in order
    - loop: Repeat forever
    - shuffle: Random once
    - endless-shuffle: Random forever
    """
```

#### Audio File Listing (`yoto_smart_stream/api/routes/cards.py`)
```python
@router.get("/audio/list")
async def list_audio_files(user: User = Depends(require_auth)):
    """
    List audio files from S3 or local directory.
    Includes: filename, size, duration, transcript status, URL
    """
```

#### Audio Streaming (`yoto_smart_stream/api/routes/cards.py`)
```python
@router.get("/audio/{filename}")
async def stream_audio(filename: str):
    """
    Stream single audio file from S3 or local directory.
    Returns StreamingResponse with proper headers for seeking.
    """
```

## Testing

### Test Coverage (`test_s3_audio_integration.py`)
1. ✅ S3 enabled detection
2. ✅ S3 bucket configuration
3. ✅ Audio file listing from S3
4. ✅ Object exists checks
5. ✅ Stream generator with S3
6. ✅ Audio file upload endpoint
7. ✅ Stream queue with S3 files
8. ✅ Dynamic streaming fallback
9. ✅ Audio endpoint S3 streaming
10. ✅ Bucket creation parameters
11. ✅ CORS configuration
12. ✅ Lifecycle rules
13. ✅ Lambda IAM permissions
14. ✅ Environment variable configuration

### Manual Testing
To test S3 audio streaming:

1. **Upload audio file**
   ```bash
   curl -X POST "http://localhost:8080/api/audio/upload" \
     -F "file=@story.mp3"
   ```

2. **List audio files**
   ```bash
   curl "http://localhost:8080/api/audio/list"
   ```

3. **Stream audio file**
   ```bash
   curl "http://localhost:8080/api/audio/story.mp3" -o story-downloaded.mp3
   ```

4. **Create stream queue**
   ```bash
   curl -X POST "http://localhost:8080/api/streams/my-story/queue" \
     -H "Content-Type: application/json" \
     -d '{"files": ["story.mp3", "chapter2.mp3"]}'
   ```

5. **Stream queue as continuous audio**
   ```bash
   curl "http://localhost:8080/api/streams/my-story/stream.mp3" -o queue.mp3
   ```

## Configuration

### Environment Variables
- `S3_AUDIO_BUCKET`: Name of S3 bucket (automatically set by CDK)
- `AUDIO_FILES_DIR`: Local fallback directory (default: `/tmp/audio_files`)
- `AWS_LAMBDA_FUNCTION_NAME`: Set automatically by Lambda runtime

### CDK Stack Configuration
```python
# Audio bucket created with:
audio_bucket = s3.Bucket(
    name=f"yoto-audio-{env}-{account}",
    versioned=is_production,  # Versioning in prod only
    cors=[...],  # Allow cross-origin requests
    lifecycle_rules=[...],  # Clean old versions
    removal_policy=RemovalPolicy.RETAIN if prod else RemovalPolicy.DESTROY,
)

# Lambda environment:
"S3_AUDIO_BUCKET": audio_bucket.bucket_name,
```

## Local Development Fallback

When not running on Lambda or S3 bucket not configured:
- Audio files stored in `audio_files/` directory
- All S3 operations transparently use local filesystem
- No code changes needed - automatic detection via `s3_enabled()`

### Local Testing
```bash
# Create local audio files
mkdir -p audio_files
python examples/generate_sample_audio.py

# Start server
python -m yoto_smart_stream

# Audio files served from local directory automatically
```

## Performance Optimizations

1. **Lambda Extension Caching**: OAuth tokens cached with 1000ms TTL
2. **S3 Streaming Chunks**: 64KB chunks for efficient streaming
3. **Byte-Range Support**: Enable client-side seeking
4. **CORS Caching**: 1-hour cache on audio files
5. **Stream Concatenation**: Efficient concatenation of multiple files

## Security

1. **IAM Permissions**: Least privilege - only needed S3 actions
2. **Bucket Versioning**: Track changes in production
3. **Public Access Block**: Enforced by default
4. **CORS Restricted**: Only necessary headers and methods
5. **Signed URLs**: Optional for time-limited access

## Deployment Status

✅ **Complete and Production Ready**

### Deployed Resources
- ✅ S3 audio bucket created by CDK
- ✅ Lambda function configured with S3 permissions
- ✅ API endpoints integrated with S3
- ✅ Local fallback implemented
- ✅ Error handling and logging
- ✅ Integration tests created

### Version
- **Current**: v0.3.2+dynamodb
- **S3 Integration**: Complete
- **Local Fallback**: Complete
- **API Endpoints**: Complete

## Related Documentation

- [Architecture Documentation](docs/ARCHITECTURE.md)
- [Audio Streaming Guide](docs/DYNAMIC_STREAMING.md)
- [Streaming from Own Service](docs/STREAMING_FROM_OWN_SERVICE.md)
- [Creating MYO Cards](docs/CREATING_MYO_CARDS.md)

## Summary

The S3 audio_files implementation provides:
✅ Scalable audio storage in AWS S3
✅ Efficient streaming with Lambda Extension caching
✅ Transparent local fallback for development
✅ Complete API for audio management
✅ Production-ready security and performance
✅ Comprehensive test coverage
✅ Clear documentation and examples

The implementation is **complete, tested, and deployed** on AWS.
