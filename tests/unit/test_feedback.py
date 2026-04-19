"""Unit tests for feedback service."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chat_service.services.feedback import (
    _build_cache_key,
    get_feedback_state,
    get_feedback_stats,
    store_feedback,
)


class TestBuildCacheKey:
    def test_with_thread_and_message(self):
        tenant_id = "00000000-0000-4000-a000-000000000001"
        thread_id = "00000000-0000-4000-a000-000000000002"
        message_id = "00000000-0000-4000-a000-000000000003"

        key = _build_cache_key(tenant_id, thread_id, message_id)
        assert key == f"feedback:stats:{tenant_id}:{thread_id}:{message_id}"

    def test_with_thread_only(self):
        tenant_id = "00000000-0000-4000-a000-000000000001"
        thread_id = "00000000-0000-4000-a000-000000000002"

        key = _build_cache_key(tenant_id, thread_id)
        assert key == f"feedback:stats:{tenant_id}:{thread_id}"

    def test_with_tenant_only(self):
        tenant_id = "00000000-0000-4000-a000-000000000001"

        key = _build_cache_key(tenant_id)
        assert key == f"feedback:stats:{tenant_id}"


def _create_async_cm_mock(conn):
    """Create a mock async context manager that returns conn."""
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=conn)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    return mock_cm


class TestStoreFeedback:
    @pytest.mark.asyncio
    async def test_inserts_new_feedback(self):
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock()

        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=_create_async_cm_mock(mock_conn))

        tenant_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        with patch("chat_service.services.feedback.tenant_db_context"):
            result = await store_feedback(
                db_pool=mock_pool,
                thread_id=thread_id,
                message_id=message_id,
                user_id=user_id,
                tenant_id=tenant_id,
                feedback_type="thumbs_up",
            )

        assert result == "thumbs_up"
        mock_conn.execute.assert_called()

    @pytest.mark.asyncio
    async def test_toggles_off_same_feedback(self):
        mock_existing = {"id": uuid.uuid4(), "feedback_type": "thumbs_up"}

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_existing)
        mock_conn.execute = AsyncMock()

        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=_create_async_cm_mock(mock_conn))

        tenant_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        with patch("chat_service.services.feedback.tenant_db_context"):
            result = await store_feedback(
                db_pool=mock_pool,
                thread_id=thread_id,
                message_id=message_id,
                user_id=user_id,
                tenant_id=tenant_id,
                feedback_type="thumbs_up",
            )

        assert result is None
        assert any("DELETE" in str(call) for call in mock_conn.execute.call_args_list)

    @pytest.mark.asyncio
    async def test_updates_existing_feedback(self):
        mock_existing = {"id": uuid.uuid4(), "feedback_type": "thumbs_up"}

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_existing)
        mock_conn.execute = AsyncMock()

        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=_create_async_cm_mock(mock_conn))

        tenant_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        with patch("chat_service.services.feedback.tenant_db_context"):
            result = await store_feedback(
                db_pool=mock_pool,
                thread_id=thread_id,
                message_id=message_id,
                user_id=user_id,
                tenant_id=tenant_id,
                feedback_type="thumbs_down",
            )

        assert result == "thumbs_down"
        assert any("UPDATE" in str(call) for call in mock_conn.execute.call_args_list)


class TestGetFeedbackState:
    @pytest.mark.asyncio
    async def test_returns_existing_feedback(self):
        mock_result = {"feedback_type": "thumbs_up"}

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_result)

        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=_create_async_cm_mock(mock_conn))

        tenant_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        with patch("chat_service.services.feedback.tenant_db_context"):
            result = await get_feedback_state(
                db_pool=mock_pool,
                thread_id=thread_id,
                message_id=message_id,
                user_id=user_id,
                tenant_id=tenant_id,
            )

        assert result == "thumbs_up"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_feedback(self):
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=_create_async_cm_mock(mock_conn))

        tenant_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        with patch("chat_service.services.feedback.tenant_db_context"):
            result = await get_feedback_state(
                db_pool=mock_pool,
                thread_id=thread_id,
                message_id=message_id,
                user_id=user_id,
                tenant_id=tenant_id,
            )

        assert result is None


class TestGetFeedbackStats:
    @pytest.mark.asyncio
    async def test_returns_zero_when_no_feedback(self):
        mock_result = {"total": 0, "thumbs_up": 0, "thumbs_down": 0}

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_result)

        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=_create_async_cm_mock(mock_conn))

        tenant_id = str(uuid.uuid4())

        with patch("chat_service.services.feedback.tenant_db_context"):
            with patch("chat_service.services.feedback.get_redis", return_value=None):
                result = await get_feedback_stats(
                    db_pool=mock_pool,
                    tenant_id=tenant_id,
                )

        assert result["total"] == 0
        assert result["thumbs_up"] == 0
        assert result["thumbs_down"] == 0
        assert result["thumbs_up_percentage"] is None
        assert result["thumbs_down_percentage"] is None

    @pytest.mark.asyncio
    async def test_returns_statistics_with_percentages(self):
        mock_result = {"total": 10, "thumbs_up": 8, "thumbs_down": 2}

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_result)

        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=_create_async_cm_mock(mock_conn))

        tenant_id = str(uuid.uuid4())

        with patch("chat_service.services.feedback.tenant_db_context"):
            with patch("chat_service.services.feedback.get_redis", return_value=None):
                result = await get_feedback_stats(
                    db_pool=mock_pool,
                    tenant_id=tenant_id,
                )

        assert result["total"] == 10
        assert result["thumbs_up"] == 8
        assert result["thumbs_down"] == 2
        assert result["thumbs_up_percentage"] == 80.0
        assert result["thumbs_down_percentage"] == 20.0

    @pytest.mark.asyncio
    async def test_filters_by_thread_id(self):
        mock_result = {"total": 5, "thumbs_up": 3, "thumbs_down": 2}

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_result)

        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=_create_async_cm_mock(mock_conn))

        tenant_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())

        with patch("chat_service.services.feedback.tenant_db_context"):
            with patch("chat_service.services.feedback.get_redis", return_value=None):
                result = await get_feedback_stats(
                    db_pool=mock_pool,
                    tenant_id=tenant_id,
                    thread_id=thread_id,
                )

        assert result["total"] == 5
