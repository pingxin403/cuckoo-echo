"""Customer Success metrics, health scores, and proactive interventions."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class HealthLevel(Enum):
    HEALTHY = "healthy"
    AT_RISK = "at_risk"
    UNHEALTHY = "unhealthy"


class RiskType(Enum):
    DECLINING_USAGE = "declining_usage"
    NEGATIVE_SENTIMENT = "negative_sentiment"
    SUPPORT_ESCALATION = "support_escalation"
    NON_RENEWAL = "non_renewal"


@dataclass
class HealthMetrics:
    login_frequency: float = 0.0
    conversation_volume: float = 0.0
    feature_adoption: float = 0.0
    self_service_rate: float = 0.0
    sentiment_score: float = 0.0
    support_ticket_count: int = 0
    nps_score: Optional[int] = None


@dataclass
class CustomerHealth:
    tenant_id: str
    health_score: float = 0.0
    health_level: HealthLevel = HealthLevel.HEALTHY
    risk_indicators: list = field(default_factory=lambda: [])
    metrics: HealthMetrics = field(default_factory=HealthMetrics)
    last_updated: datetime = field(default_factory=datetime.utcnow)


class HealthCalculator:
    USAGE_WEIGHT = 0.25
    ENGAGEMENT_WEIGHT = 0.35
    SENTIMENT_WEIGHT = 0.40

    @classmethod
    def calculate_score(cls, metrics: HealthMetrics) -> float:
        usage = cls._calculate_usage_score(metrics)
        engagement = cls._calculate_engagement_score(metrics)
        sentiment = cls._calculate_sentiment_score(metrics)
        
        return (
            usage * cls.USAGE_WEIGHT +
            engagement * cls.ENGAGEMENT_WEIGHT +
            sentiment * cls.SENTIMENT_WEIGHT
        )

    @classmethod
    def _calculate_usage_score(cls, metrics: HealthMetrics) -> float:
        login_score = min(metrics.login_frequency / 20, 1.0)
        volume_score = min(metrics.conversation_volume / 100, 1.0)
        return (login_score + volume_score) / 2

    @classmethod
    def _calculate_engagement_score(cls, metrics: HealthMetrics) -> float:
        adoption_score = metrics.feature_adoption
        self_service_score = metrics.self_service_rate
        return (adoption_score + self_service_score) / 2

    @classmethod
    def _calculate_sentiment_score(cls, metrics: HealthMetrics) -> float:
        if metrics.nps_score is not None:
            nps_normalized = (metrics.nps_score + 1) / 10
        else:
            nps_normalized = metrics.sentiment_score
        
        ticket_ratio = min(metrics.support_ticket_count / 10, 1.0)
        ticket_penalty = 1.0 - ticket_ratio
        
        return (nps_normalized + ticket_penalty) / 2

    @classmethod
    def determine_level(cls, score: float) -> HealthLevel:
        if score >= 0.7:
            return HealthLevel.HEALTHY
        elif score >= 0.4:
            return HealthLevel.AT_RISK
        return HealthLevel.UNHEALTHY

    @classmethod
    def detect_risks(cls, metrics: HealthMetrics, historical: list) -> list:
        risks = []
        
        if len(historical) >= 3:
            recent_volume = sum(m.conversation_volume for m in historical[-3:]) / 3
            if metrics.conversation_volume < recent_volume * 0.5:
                risks.append(RiskType.DECLINING_USAGE)
        
        if metrics.sentiment_score < 0.3 or (metrics.nps_score or 10) < 5:
            risks.append(RiskType.NEGATIVE_SENTIMENT)
        
        if metrics.support_ticket_count > 5:
            risks.append(RiskType.SUPPORT_ESCALATION)
        
        return risks


@dataclass
class Intervention:
    tenant_id: str
    intervention_type: str
    triggered_by: RiskType
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.utcnow)


class InterventionService:
    def __init__(self) -> None:
        self.interventions: dict = {}

    def trigger_intervention(self, tenant_id: str, intervention_type: str, risk: RiskType) -> Intervention:
        if tenant_id not in self.interventions:
            self.interventions[tenant_id] = []
        
        intervention = Intervention(
            tenant_id=tenant_id,
            intervention_type=intervention_type,
            triggered_by=risk,
        )
        self.interventions[tenant_id].append(intervention)
        return intervention

    def get_pending(self, tenant_id: str) -> list:
        return [
            i for i in self.interventions.get(tenant_id, [])
            if i.status == "pending"
        ]


class CustomerSuccessService:
    def __init__(self) -> None:
        self.health_cache: dict = {}
        self.intervention_service = InterventionService()

    def calculate_health(self, tenant_id: str, metrics: HealthMetrics) -> CustomerHealth:
        health_score = HealthCalculator.calculate_score(metrics)
        health_level = HealthCalculator.determine_level(health_score)
        historical = self._get_historical_metrics(tenant_id)
        risk_indicators = HealthCalculator.detect_risks(metrics, historical)
        
        health = CustomerHealth(
            tenant_id=tenant_id,
            health_score=health_score,
            health_level=health_level,
            risk_indicators=risk_indicators,
            metrics=metrics,
        )
        
        self.health_cache[tenant_id] = health
        
        for risk in risk_indicators:
            self._trigger_interventions(tenant_id, risk)
        
        return health

    def _get_historical_metrics(self, tenant_id: str) -> list:
        return []

    def _trigger_interventions(self, tenant_id: str, risk: RiskType) -> None:
        if risk == RiskType.DECLINING_USAGE:
            self.intervention_service.trigger_intervention(tenant_id, "re_engage_email", risk)
        elif risk == RiskType.NEGATIVE_SENTIMENT:
            self.intervention_service.trigger_intervention(tenant_id, "success_manager_alert", risk)
        elif risk == RiskType.SUPPORT_ESCALATION:
            self.intervention_service.trigger_intervention(tenant_id, "priority_support", risk)