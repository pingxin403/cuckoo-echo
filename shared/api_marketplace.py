"""API Marketplace for third-party integrations."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
import uuid
import hashlib
import secrets


class APIKeyStatus(Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"


class PlanTier(Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


@dataclass
class Developer:
    id: str
    email: str
    name: str
    company: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "active"


@dataclass
class APIKey:
    id: str
    developer_id: str
    key_hash: str
    name: str
    status: APIKeyStatus = APIKeyStatus.ACTIVE
    tier: PlanTier = PlanTier.FREE
    rate_limit: int = 100
    monthly_quota: int = 1000
    usage_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None


@dataclass
class UsageRecord:
    api_key_id: str
    endpoint: str
    method: str
    status_code: int
    tokens_used: int = 0
    latency_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RateLimitConfig:
    requests_per_minute: int = 60
    requests_per_day: int = 1000
    tokens_per_day: int = 100000


class APIMarketplace:
    def __init__(self) -> None:
        self.developers: dict = {}
        self.api_keys: dict = {}
        self.usage_records: list = []
        self.rate_limits: dict = {}

    def register_developer(self, email: str, name: str, company: Optional[str] = None) -> Developer:
        developer = Developer(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            company=company,
        )
        self.developers[developer.id] = developer
        return developer

    def generate_api_key(
        self,
        developer_id: str,
        name: str,
        tier: PlanTier = PlanTier.FREE,
        rate_limit: int = 100,
        monthly_quota: int = 1000,
    ) -> tuple:
        raw_key = f"sk_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        api_key = APIKey(
            id=str(uuid.uuid4()),
            developer_id=developer_id,
            key_hash=key_hash,
            name=name,
            tier=tier,
            rate_limit=rate_limit,
            monthly_quota=monthly_quota,
        )
        
        self.api_keys[api_key.id] = api_key
        return api_key, raw_key

    def verify_api_key(self, raw_key: str) -> Optional[APIKey]:
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        for api_key in self.api_keys.values():
            if api_key.key_hash == key_hash:
                if api_key.status == APIKeyStatus.ACTIVE:
                    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
                        api_key.status = APIKeyStatus.EXPIRED
                        return None
                    return api_key
                return None
        return None

    def record_usage(self, api_key_id: str, record: UsageRecord) -> None:
        if api_key_id in self.api_keys:
            self.api_keys[api_key_id].usage_count += 1
            self.api_keys[api_key_id].last_used = datetime.utcnow()
        self.usage_records.append(record)

    def check_rate_limit(self, api_key: APIKey) -> bool:
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        
        recent_usage = [
            r for r in self.usage_records
            if r.api_key_id == api_key.id and r.timestamp > minute_ago
        ]
        
        return len(recent_usage) < api_key.rate_limit

    def get_usage_summary(self, api_key_id: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> dict:
        records = [r for r in self.usage_records if r.api_key_id == api_key_id]
        
        if start_date:
            records = [r for r in records if r.timestamp >= start_date]
        if end_date:
            records = [r for r in records if r.timestamp <= end_date]
        
        return {
            "total_requests": len(records),
            "tokens_used": sum(r.tokens_used for r in records),
            "avg_latency_ms": sum(r.latency_ms for r in records) / len(records) if records else 0,
            "by_endpoint": self._aggregate_by_endpoint(records),
        }

    def _aggregate_by_endpoint(self, records: list) -> dict:
        by_endpoint: dict = {}
        for r in records:
            by_endpoint[r.endpoint] = by_endpoint.get(r.endpoint, 0) + 1
        return by_endpoint

    def revoke_api_key(self, api_key_id: str) -> bool:
        if api_key_id in self.api_keys:
            self.api_keys[api_key_id].status = APIKeyStatus.SUSPENDED
            return True
        return False


marketplace = APIMarketplace()