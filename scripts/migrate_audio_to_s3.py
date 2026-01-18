#!/usr/bin/env python3
"""
Migrate audio files from Railway volume to Railway Bucket.

This script copies audio files from the local filesystem (Railway persistent volume)
to S3-compatible Railway Buckets. Run this once per environment after the bucket
is provisioned and STORAGE_BACKEND=s3 is configured.

Usage:
    python scripts/migrate_audio_to_s3.py [--dry-run] [--delete-after]

Options:
    --dry-run        Show what would be migrated without actually copying files
    --delete-after   Delete files from local storage after successful migration (use with caution!)

Environment Variables Required:
    STORAGE_BACKEND=s3
    BUCKET=<bucket-name>
    ACCESS_KEY_ID=<access-key>
    SECRET_ACCESS_KEY=<secret-key>
    ENDPOINT=https://storage.railway.app (optional, defaults to Railway)
    REGION=auto (optional, defaults to auto)
"""

import asyncio
import sys


async def main():
    """Main migration function."""
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Migrate audio files from volume to S3")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated")
    parser.add_argument(
        "--delete-after",
        action="store_true",
        help="Delete local files after successful migration",
    )
    args = parser.parse_args()

    # Import after argparse to allow --help without dependencies
    from yoto_smart_stream.config import get_settings

    settings = get_settings()

    # Validate configuration
    if settings.storage_backend != "s3":
        print("ERROR: STORAGE_BACKEND must be set to 's3' to run migration")
        print("Current value:", settings.storage_backend)
        return 1

    if not settings.bucket_name:
        print("ERROR: BUCKET environment variable not set")
        return 1

    if not settings.bucket_access_key_id:
        print("ERROR: ACCESS_KEY_ID environment variable not set")
        return 1

    if not settings.bucket_secret_access_key:
        print("ERROR: SECRET_ACCESS_KEY environment variable not set")
        return 1

    print("=" * 60)
    print("AUDIO FILE MIGRATION: Volume → S3 Bucket")
    print("=" * 60)
    print(f"Environment: {settings.environment}")
    print(f"Source: {settings.audio_files_dir}")
    print(f"Destination: s3://{settings.bucket_name}")
    print(f"Endpoint: {settings.bucket_endpoint}")
    print(f"Dry Run: {args.dry_run}")
    print(f"Delete After: {args.delete_after}")
    print("=" * 60)
    print()

    # Get S3 storage instance
    s3_storage = settings.get_storage()  # Will return S3Storage based on config

    # Find all MP3 files in local storage
    audio_files = list(settings.audio_files_dir.glob("*.mp3"))

    if not audio_files:
        print("No audio files found to migrate.")
        return 0

    print(f"Found {len(audio_files)} audio file(s) to migrate")
    print()

    # Migrate each file
    migrated = 0
    skipped = 0
    failed = 0

    for audio_path in sorted(audio_files):
        filename = audio_path.name
        file_size = audio_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)

        print(f"Processing: {filename} ({file_size_mb:.2f} MB)")

        try:
            # Check if file already exists in S3
            exists_in_s3 = await s3_storage.exists(filename)

            if exists_in_s3:
                s3_size = await s3_storage.get_file_size(filename)
                if s3_size == file_size:
                    print(f"  ✓ Already migrated (size matches: {file_size} bytes)")
                    skipped += 1
                    continue
                else:
                    print(f"  ⚠ Exists in S3 but size differs (local: {file_size}, S3: {s3_size})")
                    print("  → Re-uploading...")

            if args.dry_run:
                print(f"  [DRY RUN] Would upload {filename}")
                migrated += 1
            else:
                # Read file data
                file_data = audio_path.read_bytes()

                # Upload to S3
                await s3_storage.save(filename, file_data)

                # Verify upload
                uploaded_size = await s3_storage.get_file_size(filename)
                if uploaded_size == file_size:
                    print(f"  ✓ Migrated successfully (verified size: {uploaded_size} bytes)")
                    migrated += 1

                    # Delete local file if requested
                    if args.delete_after:
                        audio_path.unlink()
                        print("  ✓ Deleted from local storage")
                else:
                    print(
                        f"  ✗ Upload verification failed (expected: {file_size}, got: {uploaded_size})"
                    )
                    failed += 1

        except Exception as e:
            print(f"  ✗ Migration failed: {e}")
            failed += 1

        print()

    # Print summary
    print("=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Total files: {len(audio_files)}")
    print(f"Migrated: {migrated}")
    print(f"Skipped (already migrated): {skipped}")
    print(f"Failed: {failed}")
    print("=" * 60)

    if args.dry_run:
        print()
        print("This was a dry run. No files were actually migrated.")
        print("Run without --dry-run to perform the migration.")
    elif failed == 0 and migrated > 0:
        print()
        print("✓ Migration completed successfully!")
        if not args.delete_after:
            print()
            print("Local files remain in:", settings.audio_files_dir)
            print("You can delete them manually after verifying S3 storage works correctly.")
            print("Or re-run with --delete-after to automatically delete local files.")
    elif failed > 0:
        print()
        print("⚠ Some files failed to migrate. Please check errors above.")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
