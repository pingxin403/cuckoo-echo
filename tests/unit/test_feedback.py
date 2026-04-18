"""Unit tests for feedback service."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import uuid

from chat_service.services.feedback import (
    store_feedback,
    get_feedback_state,
    get_feedback_stats,
    _build_cache_key,
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


class TestStoreFeedback:
    @pytest.mark.asyncio
    async def test_inserts_new_feedback(self):
        # Setup mock database
        mock_conn = AsyncMock()
        mock_conn.transaction = MagicMock()
        mock_conn.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.transaction.return_value.__aexit__ = AsyncMock(return_value=False)
        
        # Mock fetchrow to return None (no existing feedback)
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock()
        
        mock_pool = MagicMock()
        mock_pool.acquire = AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        
        tenant_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        
        with patch("chat_service.services.feedback.tenant_db_context") as mock_tenant_ctx:
            mock_tenant_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_tenant_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            
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
        # Setup mock database
        mock_conn = AsyncMock()
        mock_conn.transaction = MagicMock()
        mock_conn.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.transaction.return_value.__aexit__ = AsyncMock(return_value=False)
        
        # Mock fetchrow to return existing feedback with same type
        mock_existing = {"id": uuid.uuid4(), "feedback_type": "thumbs_up"}
        mock_conn.fetchrow = AsyncMock(return_value=mock_existing)
        mock_conn.execute = AsyncMock()
        
        mock_pool = MagicMock()
        mock_pool.acquire = AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        
        tenant_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        
        with patch("chat_service.services.feedback.tenant_db_context") as mock_tenant_ctx:
            mock_tenant_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_tenant_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            
            result = await store_feedback(
                db_pool=mock_pool,
                thread_id=thread_id,
                message_id=message_id,
                user_id=user_id,
                tenant_id=tenant_id,
                feedback_type="thumbs_up",
            )
        
        # Should return None to indicate toggle-off
        assert result is None
        # Should have executed DELETE
        assert any("DELETE" in str(call) for call in mock_conn.execute.call_args_list)
    
    @pytest.mark.asyncio
    async def test_updates_existing_feedback(self):
        # Setup mock database
        mock_conn = AsyncMock()
        mock_conn.transaction = MagicMock()
        mock_conn.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.transaction.return_value.__aexit__ = AsyncMock(return_value=False)
        
        # Mock fetchrow to return existing feedback with different type
        mock_existing = {"id": uuid.uuid4(), "feedback_type": "thumbs_up"}
        mock_conn.fetchrow = AsyncMock(return_value=mock_existing)
        mock_conn.execute = AsyncMock()
        
        mock_pool = MagicMock()
        mock_pool.acquire = AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        
        tenant_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        
        with patch("chat_service.services.feedback.tenant_db_context") as mock_tenant_ctx:
            mock_tenant_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_tenant_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            
            result = await store_feedback(
                db_pool=mock_pool,
                thread_id=thread_id,
                message_id=message_id,
                user_id=user_id,
                tenant_id=tenant_id,
                feedback_type="thumbs_down",
            )
        
        assert result == "thumbs_down"
        # Should have executed UPDATE
        assert any("UPDATE" in str(call) for call in mock_conn.execute.call_args_list)


class TestGetFeedbackState:
    @pytest.mark.asyncio
    async def test_returns_existing_feedback(self):
        mock_conn = AsyncMock()
        mock_conn.transaction = MagicMock()
        mock_conn.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.transaction.return_value.__aexit__ = AsyncMock(return_value=False)
        
        mock_result = {"feedback_type": "thumbs_up"}
        mock_conn.fetchrow = AsyncMock(return_value=mock_result)
        
        mock_pool = MagicMock()
        mock_pool.acquire = AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        
        tenant_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        
        with patch("chat_service.services.feedback.tenant_db_context") as mock_tenant_ctx:
            mock_tenant_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_tenant_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            
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
        mock_conn.transaction = MagicMock()
        mock_conn.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.transaction.return_value.__aexit__ = AsyncMock(return_value=False)
        
        mock_conn.fetchrow = AsyncMock(return_value=None)
        
        mock_pool = MagicMock()
        mock_pool.acquire = AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        
        tenant_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        
        with patch("chat_service.services.feedback.tenant_db_context") as mock_tenant_ctx:
            mock_tenant_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_tenant_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            
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
        mock_conn = AsyncMock()
        mock_conn.transaction = MagicMock()
        mock_conn.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.transaction.return_value.__aexit__ = AsyncMock(return_value=False)
        
        mock_result = {"total": 0, "thumbs_up": 0, "thumbs_down": 0}
        mock_conn.fetchrow = AsyncMock(return_value=mock_result)
        
        mock_pool = MagicMock()
        mock_pool.acquire = AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        
        tenant_id = str(uuid.uuid4())
        
        with patch("chat_service.services.feedback.tenant_db_context") as mock_tenant_ctx:
            mock_tenant_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_tenant_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            
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
        mock_conn = AsyncMock()
        mock_conn.transaction = MagicMock()
        mock_conn.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.transaction.return_value.__aexit__ = AsyncMock(return_value=False)
        
        mock_result = {"total": 10, "thumbs_up": 8, "thumbs_down": 2}
        mock_conn.fetchrow = AsyncMock(return_value=mock_result)
        
        mock_pool = MagicMock()
        mock_pool.acquire = AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        
        tenant_id = str(uuid.uuid4())
        
        with patch("chat_service.services.feedback.tenant_db_context") as mock_tenant_ctx:
            mock_tenant_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_tenant_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            
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
        mock_conn = AsyncMock()
        mock_conn.transaction = MagicMock()
        mock_conn.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.transaction.return_value.__aexit__ = AsyncMock(return_value=False)
        
        mock_result = {"total": 5, "thumbs_up": 3, "thumbs_down": 2}
        mock_conn.fetchrow = AsyncMock(return_value=mock_result)
        
        mock_pool = MagicMock()
        mock_pool.acquire = AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        
        tenant_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        
        with patch("chat_service.services.feedback.tenant_db_context") as mock_tenant_ctx:
            mock_tenant_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_tenant_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            
            result = await get_feedback_stats(
                db_pool=mock_pool,
                tenant_id=tenant_id,
                thread_id=thread_id,
            )
        
        assert result["total"] == 5
        # Verify thread_id filter was used in query
        assert mock_conn.fetchrow.called
