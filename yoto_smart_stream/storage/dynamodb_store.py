"""DynamoDB-backed persistence for users and audio metadata.

This store replaces the previous SQLite layer so the service can run on
Lambda without a writable filesystem. It uses a single table with a
`PK/SK` composite key and simple prefixes for entity types.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

import boto3
from boto3.dynamodb.conditions import Attr

logger = logging.getLogger(__name__)


@dataclass
class UserRecord:
    """User data stored in DynamoDB."""

    user_id: int
    username: str
    email: Optional[str]
    hashed_password: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime
    yoto_refresh_token: Optional[str] = None
    yoto_access_token: Optional[str] = None
    yoto_token_expires_at: Optional[str] = None

    @property
    def id(self) -> int:
        """Compatibility accessor mirroring SQLAlchemy user.id."""
        return self.user_id


@dataclass
class AudioFileRecord:
    """Audio metadata stored in DynamoDB."""

    filename: str
    size: int
    duration: Optional[int]
    transcript: Optional[str]
    transcript_status: str
    transcript_error: Optional[str]
    created_at: datetime
    updated_at: datetime
    transcribed_at: Optional[datetime]


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _parse_dt(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except Exception:
        return None


def _as_int(value) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(value)
    except Exception:
        return None


class DynamoStore:
    """Typed helper around the shared DynamoDB table."""

    def __init__(self, table_name: str, region_name: Optional[str] = None):
        if not table_name:
            raise ValueError("DynamoStore requires table_name")
        region = region_name or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
        resource = boto3.resource("dynamodb", region_name=region)
        self.table = resource.Table(table_name)
        self.table_name = table_name
        self.region = region
        logger.info(f"Using DynamoDB table {table_name} in region {region}")

    # --------------------
    # User helpers
    # --------------------

    @staticmethod
    def _user_pk(username: str) -> str:
        return f"USER#{username}".lower()

    @staticmethod
    def _user_sk() -> str:
        return "PROFILE"

    def _user_item_to_record(self, item: dict) -> UserRecord:
        return UserRecord(
            user_id=_as_int(item.get("user_id")) or 0,
            username=item.get("username") or "",
            email=item.get("email"),
            hashed_password=item.get("hashed_password") or "",
            is_active=bool(item.get("is_active", True)),
            is_admin=bool(item.get("is_admin", False)),
            created_at=_parse_dt(item.get("created_at")) or _now_utc(),
            updated_at=_parse_dt(item.get("updated_at")) or _now_utc(),
            yoto_refresh_token=item.get("yoto_refresh_token"),
            yoto_access_token=item.get("yoto_access_token"),
            yoto_token_expires_at=item.get("yoto_token_expires_at"),
        )

    def list_users(self) -> List[UserRecord]:
        response = self.table.scan(
            FilterExpression=Attr("PK").begins_with("user#") & Attr("SK").eq(self._user_sk())
        )
        items = response.get("Items", [])
        return [self._user_item_to_record(item) for item in items]

    def user_count(self) -> int:
        return len(self.list_users())

    def get_user(self, username: str) -> Optional[UserRecord]:
        response = self.table.get_item(Key={"PK": self._user_pk(username), "SK": self._user_sk()})
        item = response.get("Item")
        if not item:
            return None
        return self._user_item_to_record(item)

    def get_user_by_id(self, user_id: int) -> Optional[UserRecord]:
        response = self.table.scan(
            FilterExpression=Attr("PK").begins_with("user#")
            & Attr("SK").eq(self._user_sk())
            & Attr("user_id").eq(user_id)
        )
        items = response.get("Items", [])
        if not items:
            return None
        return self._user_item_to_record(items[0])

    def create_user(self, username: str, hashed_password: str, email: Optional[str], is_admin: bool) -> UserRecord:
        now = _now_utc()
        user_id = int(now.timestamp() * 1000)
        item = {
            "PK": self._user_pk(username),
            "SK": self._user_sk(),
            "user_id": user_id,
            "username": username,
            "email": email or None,
            "hashed_password": hashed_password,
            "is_active": True,
            "is_admin": is_admin,
            "created_at": _iso(now),
            "updated_at": _iso(now),
        }

        try:
            self.table.put_item(Item=item, ConditionExpression=Attr("PK").not_exists())
        except Exception as exc:
            logger.error(f"Failed to create user {username}: {exc}")
            raise

        return self._user_item_to_record(item)

    def update_user(self, user_id: int, email: Optional[str], hashed_password: Optional[str], is_admin: Optional[bool] = None) -> Optional[UserRecord]:
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        update_expr = []
        expr_values = {":updated_at": _iso(_now_utc())}
        expr_names = {}

        if email is not None:
            update_expr.append("#email = :email")
            expr_values[":email"] = email
            expr_names["#email"] = "email"

        if hashed_password is not None:
            update_expr.append("hashed_password = :pwd")
            expr_values[":pwd"] = hashed_password

        if is_admin is not None:
            update_expr.append("is_admin = :is_admin")
            expr_values[":is_admin"] = is_admin

        if not update_expr:
            return user

        update_clause = ", ".join(update_expr + ["updated_at = :updated_at"])

        # Build update_item arguments
        update_args = {
            "Key": {"PK": self._user_pk(user.username), "SK": self._user_sk()},
            "UpdateExpression": f"SET {update_clause}",
            "ExpressionAttributeValues": expr_values,
        }
        
        # Only include ExpressionAttributeNames if we have any
        if expr_names:
            update_args["ExpressionAttributeNames"] = expr_names
        
        self.table.update_item(**update_args)

        return self.get_user(user.username)

    def delete_user(self, user_id: int) -> bool:
        """Delete a user by user_id. Returns True if deleted, False if not found."""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        try:
            self.table.delete_item(
                Key={"PK": self._user_pk(user.username), "SK": self._user_sk()}
            )
            logger.info(f"Deleted user {user.username} (id: {user_id}) from DynamoDB")
            return True
        except Exception as exc:
            logger.error(f"Failed to delete user {user.username}: {exc}")
            raise

    def save_yoto_tokens(self, username: str, refresh_token: str, access_token: Optional[str] = None, expires_at: Optional[str] = None) -> None:
        """Save Yoto OAuth tokens to DynamoDB for the specified user."""
        user = self.get_user(username)
        if not user:
            logger.error(f"Cannot save tokens: user {username} not found")
            return
        
        update_expr = ["yoto_refresh_token = :rt", "updated_at = :updated_at"]
        expr_values = {
            ":rt": refresh_token,
            ":updated_at": _iso(_now_utc())
        }
        
        if access_token:
            update_expr.append("yoto_access_token = :at")
            expr_values[":at"] = access_token
        
        if expires_at:
            update_expr.append("yoto_token_expires_at = :exp")
            expr_values[":exp"] = expires_at
        
        update_clause = ", ".join(update_expr)
        
        self.table.update_item(
            Key={"PK": self._user_pk(username), "SK": self._user_sk()},
            UpdateExpression=f"SET {update_clause}",
            ExpressionAttributeValues=expr_values
        )
        logger.info(f"✓ Yoto OAuth tokens saved to DynamoDB for user {username}")
    
    def load_yoto_tokens(self, username: str) -> Optional[tuple]:
        """Load Yoto OAuth tokens from DynamoDB.
        
        Returns:
            Tuple of (refresh_token, access_token, expires_at) or None if not found
        """
        user = self.get_user(username)
        if not user or not user.yoto_refresh_token:
            logger.debug(f"No Yoto tokens found for user {username}")
            return None
        
        logger.info(f"✓ Loaded Yoto OAuth tokens from DynamoDB for user {username}")
        return (user.yoto_refresh_token, user.yoto_access_token, user.yoto_token_expires_at)

    def ensure_admin_user(self, hashed_password: str, email: Optional[str]) -> UserRecord:
        existing = self.get_user("admin")
        if existing:
            return existing
        logger.info("Creating default admin user in DynamoDB")
        return self.create_user("admin", hashed_password, email=email, is_admin=True)

    # --------------------
    # Audio helpers
    # --------------------

    @staticmethod
    def _audio_pk(filename: str) -> str:
        return f"AUDIO#{filename}"

    @staticmethod
    def _audio_sk() -> str:
        return "METADATA"

    def _audio_item_to_record(self, item: dict) -> AudioFileRecord:
        return AudioFileRecord(
            filename=item.get("filename", ""),
            size=_as_int(item.get("size")) or 0,
            duration=_as_int(item.get("duration")),
            transcript=item.get("transcript"),
            transcript_status=item.get("transcript_status", "pending"),
            transcript_error=item.get("transcript_error"),
            created_at=_parse_dt(item.get("created_at")) or _now_utc(),
            updated_at=_parse_dt(item.get("updated_at")) or _now_utc(),
            transcribed_at=_parse_dt(item.get("transcribed_at")),
        )

    def list_audio_files(self) -> List[AudioFileRecord]:
        response = self.table.scan(
            FilterExpression=Attr("PK").begins_with("AUDIO#") & Attr("SK").eq(self._audio_sk())
        )
        items = response.get("Items", [])
        return [self._audio_item_to_record(item) for item in items]

    def search_audio_files(self, query: str) -> List[AudioFileRecord]:
        if not query:
            return self.list_audio_files()
        response = self.table.scan(
            FilterExpression=Attr("PK").begins_with("AUDIO#")
            & Attr("SK").eq(self._audio_sk())
            & Attr("filename").contains(query)
        )
        items = response.get("Items", [])
        return [self._audio_item_to_record(item) for item in items]

    def get_audio_file(self, filename: str) -> Optional[AudioFileRecord]:
        response = self.table.get_item(Key={"PK": self._audio_pk(filename), "SK": self._audio_sk()})
        item = response.get("Item")
        if not item:
            return None
        return self._audio_item_to_record(item)

    def upsert_audio_file(self, filename: str, size: int, duration: Optional[int]) -> AudioFileRecord:
        now = _iso(_now_utc())
        self.table.update_item(
            Key={"PK": self._audio_pk(filename), "SK": self._audio_sk()},
            UpdateExpression=(
                "SET filename = :filename, size = :size, duration = :duration, "
                "transcript_status = if_not_exists(transcript_status, :pending), "
                "created_at = if_not_exists(created_at, :created_at), updated_at = :updated_at"
            ),
            ExpressionAttributeValues={
                ":filename": filename,
                ":size": size,
                ":duration": duration,
                ":pending": "pending",
                ":created_at": now,
                ":updated_at": now,
            },
        )
        record = self.get_audio_file(filename)
        if record is None:
            raise RuntimeError(f"Failed to read audio metadata for {filename} after upsert")
        return record

    def update_transcript(
        self,
        filename: str,
        transcript: Optional[str],
        status: str,
        error: Optional[str] = None,
    ) -> Optional[AudioFileRecord]:
        now = _iso(_now_utc())
        update_expr = ["transcript_status = :status", "updated_at = :updated_at"]
        values = {
            ":status": status,
            ":updated_at": now,
            ":error": error,
            ":transcript": transcript,
        }

        if transcript is not None:
            update_expr.append("transcript = :transcript")
        if error is not None:
            update_expr.append("transcript_error = :error")
        else:
            update_expr.append("transcript_error = :error")  # clears when None
        if status == "completed":
            update_expr.append("transcribed_at = :updated_at")

        self.table.update_item(
            Key={"PK": self._audio_pk(filename), "SK": self._audio_sk()},
            UpdateExpression="SET " + ", ".join(update_expr),
            ExpressionAttributeValues=values,
        )
        return self.get_audio_file(filename)

    def set_transcript_status(self, filename: str, status: str, error: Optional[str] = None) -> Optional[AudioFileRecord]:
        return self.update_transcript(filename, transcript=None, status=status, error=error)


_store: Optional[DynamoStore] = None


def get_store(table_name: Optional[str] = None, region_name: Optional[str] = None) -> DynamoStore:
    global _store
    if _store is None:
        table = table_name or os.getenv("DYNAMODB_TABLE")
        if not table:
            raise ValueError("DYNAMODB_TABLE is not configured")
        _store = DynamoStore(table, region_name=region_name)
    return _store
