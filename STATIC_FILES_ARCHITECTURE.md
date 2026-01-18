# Static Files Architecture

## Overview

As of v0.3.12, all static files (HTML, CSS, JS, images) are served from Amazon S3 instead of being bundled in the Lambda deployment package. This resolves deployment errors caused by duplicate static files and reduces Lambda cold start times.

## Architecture

```
┌──────────────────┐
│   User Browser   │
└────────┬─────────┘
         │ GET /
         │ GET /static/css/style.css
         ▼
┌──────────────────────────┐
│  API Gateway + Lambda    │
│  (FastAPI Application)   │
└────────┬─────────────────┘
         │ S3 GetObject
         ▼
┌──────────────────────────┐
│  S3 UI Bucket            │
│  yoto-ui-{env}-{account} │
│  - index.html            │
│  - login.html            │
│  - css/style.css         │
│  - js/dashboard.js       │
│  - ...                   │
└──────────────────────────┘
```

## File Locations

### Served from S3
**All files** in `yoto_smart_stream/static/` are uploaded to S3 during CDK deployment:

- **HTML files**: `index.html`, `login.html`, `streams.html`, `library.html`, `audio-library.html`, `admin.html`
- **CSS files**: `css/style.css`
- **JavaScript files**: `js/*.js` (dashboard.js, streams.js, library.js, admin.js, audio-library.js, mqtt-analyzer.js)
- **Images**: Any images in `static/` directory

### Bundled in Lambda Package (REQUIRED Exceptions)
**Python code only** - no static assets:

- `handler.py` - Lambda entry point
- `yoto_smart_stream/` Python package
- Python dependencies in `package/` directory

**Rationale for Exceptions:**
1. **Lambda size limits** - 250 MB unzipped, 50 MB zipped
2. **Deployment speed** - Smaller package = faster cold starts
3. **Caching** - S3 serves files with proper cache headers
4. **Separation of concerns** - Static content vs. application logic

## Serving Mechanism

### FastAPI S3 Proxy

Static files are fetched from S3 on-demand using boto3:

```python
@app.get("/static/{file_path:path}")
async def serve_static(file_path: str):
    response = s3_client.get_object(
        Bucket=ui_bucket_name,
        Key=file_path
    )
    content = response['Body'].read()
    return Response(content=content, media_type=content_type)
```

### Fallback Behavior

For development environments where S3 may not be available:
1. Try S3 first (if `S3_UI_BUCKET` environment variable is set)
2. Fall back to local filesystem (`yoto_smart_stream/static/`)
3. Return 404 if file not found in either location

## Deployment Process

### CDK Deployment

The CDK stack automatically uploads static files to S3:

```python
s3_deployment.BucketDeployment(
    self,
    "StaticFilesDeployment",
    sources=[s3_deployment.Source.asset("../../yoto_smart_stream/static")],
    destination_bucket=self.ui_bucket,
    prune=True,  # Remove old files
)
```

### Deployment Steps

1. **CDK synth** - Packages static files
2. **CDK deploy** - Uploads static files to S3 bucket
3. **Lambda deployment** - Deploys Python code only (no static files)
4. **CloudFormation** - Updates Lambda environment with `S3_UI_BUCKET` variable

## Development Workflow

### Local Development

Static files served from local filesystem:

```bash
# Run locally (S3_UI_BUCKET not set)
python -m yoto_smart_stream

# Static files served from yoto_smart_stream/static/
```

### AWS Development

Static files served from S3:

```bash
# Deploy to dev
cd infrastructure/cdk
cdk deploy -c environment=dev -c yoto_client_id="Pcht77vFlFIWF9xro2oPUBEtCYJr8zuO" -c enable_mqtt=true

# Static files uploaded to: s3://yoto-ui-dev-{account}/
# Lambda environment: S3_UI_BUCKET=yoto-ui-dev-{account}
```

## Troubleshooting

### Static Files Not Loading (404)

Check if files are in S3:
```bash
aws s3 ls s3://yoto-ui-dev-{account}/ --recursive
```

Re-deploy CDK to upload files:
```bash
cd infrastructure/cdk
cdk deploy -c environment=dev
```

### Lambda Package Too Large

Ensure static files are NOT in Lambda package:
```bash
cd infrastructure/lambda
du -sh package/
# Should be < 50 MB
```

## Benefits

1. **Reduced Lambda Package Size** - ~50% smaller without static files
2. **Faster Cold Starts** - Smaller package = faster initialization
3. **Better Caching** - S3 serves files with proper cache headers
4. **Easier Updates** - Update static files without Lambda redeployment
5. **Cost Optimization** - S3 storage cheaper than Lambda package storage

## Future Enhancements

1. **CloudFront Integration** - Add CloudFront distribution for production
2. **Cache Invalidation** - Automate cache invalidation on deployment
3. **Versioned Assets** - Add cache-busting hashes to filenames
4. **Compression** - Enable gzip compression for text files
