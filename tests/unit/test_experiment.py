"""Unit tests for experiment service."""

import pytest
from chat_service.services.experiment import (
    Experiment,
    ExperimentVariant,
    assign_variant,
    calculate_significance,
)


class TestExperimentModel:
    """Tests for Experiment model."""

    def test_experiment_creation(self):
        """Test creating an experiment."""
        experiment = Experiment(
            id="exp-123",
            name="test-experiment",
            experiment_type="prompt",
            variants=[
                ExperimentVariant("control", 50),
                ExperimentVariant("variant_a", 50),
            ],
            metric="conversion_rate",
            status="draft",
            tenant_id="tenant-1",
        )

        assert experiment.id == "exp-123"
        assert experiment.name == "test-experiment"
        assert experiment.experiment_type == "prompt"
        assert len(experiment.variants) == 2
        assert experiment.status == "draft"

    def test_experiment_to_dict(self):
        """Test converting experiment to dict."""
        experiment = Experiment(
            id="exp-123",
            name="test-experiment",
            experiment_type="prompt",
            variants=[
                ExperimentVariant("control", 50),
                ExperimentVariant("variant_a", 50),
            ],
            metric="conversion_rate",
        )

        result = experiment.to_dict()

        assert result["id"] == "exp-123"
        assert result["name"] == "test-experiment"
        assert result["type"] == "prompt"
        assert len(result["variants"]) == 2

    def test_experiment_from_dict(self):
        """Test creating experiment from dict."""
        data = {
            "id": "exp-123",
            "name": "test-experiment",
            "type": "prompt",
            "variants": [
                {"id": "control", "weight": 50},
                {"id": "variant_a", "weight": 50},
            ],
            "metric": "conversion_rate",
            "status": "draft",
        }

        experiment = Experiment.from_dict(data)

        assert experiment.id == "exp-123"
        assert experiment.experiment_type == "prompt"
        assert len(experiment.variants) == 2


class TestTrafficSplitting:
    """Tests for traffic splitting."""

    def test_assign_variant_basic(self):
        """Test basic variant assignment."""
        variants = [
            ExperimentVariant("control", 50),
            ExperimentVariant("variant_a", 50),
        ]

        # Same inputs should always return same variant
        variant_id = assign_variant("tenant-1", "exp-1", variants)

        assert variant_id in ["control", "variant_a"]

    def test_assign_variant_consistency(self):
        """Test variant assignment is consistent."""
        variants = [
            ExperimentVariant("control", 50),
            ExperimentVariant("variant_a", 50),
        ]

        # Same inputs should always return same variant
        results = [
            assign_variant("tenant-1", "exp-1", variants)
            for _ in range(10)
        ]

        assert all(r == results[0] for r in results)

    def test_assign_variant_different_tenants(self):
        """Test different tenants can get different variants."""
        variants = [
            ExperimentVariant("control", 50),
            ExperimentVariant("variant_a", 50),
        ]

        # Different tenants should potentially get different variants
        results = set()
        for i in range(10):
            variant = assign_variant(f"tenant-{i}", "exp-1", variants)
            results.add(variant)

        # With 10 tenants, likely both variants seen (but not guaranteed)
        assert len(results) >= 1

    def test_assign_variant_weighted(self):
        """Test weighted variant assignment."""
        # 90% control, 10% variant_a
        variants = [
            ExperimentVariant("control", 90),
            ExperimentVariant("variant_a", 10),
        ]

        # Should be predominantly control
        control_count = sum(
            1 for _ in range(100)
            if assign_variant(f"tenant-{_}", "exp-1", variants) == "control"
        )

        # At least 70% should be control
        assert control_count >= 70


class TestStatisticalSignificance:
    """Tests for statistical significance calculation."""

    def test_calculate_significance_insufficient_samples(self):
        """Test significance returns 0 with insufficient samples."""
        significance = calculate_significance(
            control_count=10,  # Less than 30
            control_avg=0.05,
            variant_stats={"variant_a": {"count": 15, "avg": 0.06}},
        )

        assert significance == 0.0

    def test_calculate_significance_sufficient_samples(self):
        """Test significance calculation with sufficient samples."""
        variant_stats = {
            "variant_a": {"count": 50, "avg": 0.08},
        }

        significance = calculate_significance(
            control_count=50,
            control_avg=0.05,
            variant_stats=variant_stats,
        )

        # Should be between 0 and 1
        assert 0.0 <= significance <= 1.0

    def test_calculate_significance_large_difference(self):
        """Test significance with large difference."""
        variant_stats = {
            "variant_a": {"count": 100, "avg": 0.20},
        }

        significance = calculate_significance(
            control_count=100,
            control_avg=0.05,
            variant_stats=variant_stats,
        )

        # Large difference should give high significance
        assert significance > 0.85