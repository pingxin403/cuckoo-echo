"""Unit tests for shared.milvus_client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import json

from pymilvus import DataType, FunctionType

from shared.milvus_client import (
    COLLECTION_NAME,
    create_knowledge_chunks_collection,
    get_milvus_client,
)


class TestGetMilvusClient:
    @patch("shared.milvus_client.get_settings")
    def test_default_uri(self, mock_get_settings) -> None:
        mock_settings = MagicMock()
        mock_settings.milvus_uri = "http://localhost:19530"
        mock_get_settings.return_value = mock_settings
        with patch("shared.milvus_client.MilvusClient") as mock_cls:
            get_milvus_client()
            mock_cls.assert_called_once_with(uri="http://localhost:19530")

    @patch("shared.milvus_client.get_settings")
    def test_custom_uri(self, mock_get_settings) -> None:
        mock_settings = MagicMock()
        mock_settings.milvus_uri = "http://milvus:19530"
        mock_get_settings.return_value = mock_settings
        with patch("shared.milvus_client.MilvusClient") as mock_cls:
            get_milvus_client()
            mock_cls.assert_called_once_with(uri="http://milvus:19530")


class TestCreateKnowledgeChunksCollection:
    def test_schema_fields(self) -> None:
        mock_client = MagicMock()
        mock_client.prepare_index_params.return_value = MagicMock()

        create_knowledge_chunks_collection(client=mock_client)

        call_kwargs = mock_client.create_collection.call_args
        schema = call_kwargs.kwargs["schema"]

        field_names = [f.name for f in schema.fields]
        assert field_names == [
            "id", "tenant_id", "doc_id", "chunk_text",
            "dense_vector", "sparse_vector", "created_at",
        ]

    def test_primary_key(self) -> None:
        mock_client = MagicMock()
        mock_client.prepare_index_params.return_value = MagicMock()

        create_knowledge_chunks_collection(client=mock_client)

        schema = mock_client.create_collection.call_args.kwargs["schema"]
        id_field = next(f for f in schema.fields if f.name == "id")
        assert id_field.is_primary is True
        assert id_field.dtype == DataType.VARCHAR

    def test_partition_key(self) -> None:
        mock_client = MagicMock()
        mock_client.prepare_index_params.return_value = MagicMock()

        create_knowledge_chunks_collection(client=mock_client)

        schema = mock_client.create_collection.call_args.kwargs["schema"]
        tenant_field = next(f for f in schema.fields if f.name == "tenant_id")
        assert tenant_field.is_partition_key is True

    def test_chunk_text_analyzer(self) -> None:
        mock_client = MagicMock()
        mock_client.prepare_index_params.return_value = MagicMock()

        create_knowledge_chunks_collection(client=mock_client)

        schema = mock_client.create_collection.call_args.kwargs["schema"]
        chunk_field = next(f for f in schema.fields if f.name == "chunk_text")
        assert chunk_field.dtype == DataType.VARCHAR
        assert chunk_field.params.get("enable_analyzer") is True
        # pymilvus serializes analyzer_params dict to a JSON string internally
        raw = chunk_field.params.get("analyzer_params")
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        assert parsed == {"type": "chinese"}

    def test_dense_vector_dim(self) -> None:
        mock_client = MagicMock()
        mock_client.prepare_index_params.return_value = MagicMock()

        create_knowledge_chunks_collection(client=mock_client)

        schema = mock_client.create_collection.call_args.kwargs["schema"]
        dense_field = next(f for f in schema.fields if f.name == "dense_vector")
        assert dense_field.dtype == DataType.FLOAT_VECTOR
        assert dense_field.params.get("dim") == 4096

    def test_sparse_vector_field(self) -> None:
        mock_client = MagicMock()
        mock_client.prepare_index_params.return_value = MagicMock()

        create_knowledge_chunks_collection(client=mock_client)

        schema = mock_client.create_collection.call_args.kwargs["schema"]
        sparse_field = next(f for f in schema.fields if f.name == "sparse_vector")
        assert sparse_field.dtype == DataType.SPARSE_FLOAT_VECTOR

    def test_bm25_function(self) -> None:
        mock_client = MagicMock()
        mock_client.prepare_index_params.return_value = MagicMock()

        create_knowledge_chunks_collection(client=mock_client)

        schema = mock_client.create_collection.call_args.kwargs["schema"]
        assert len(schema.functions) == 1
        bm25_fn = schema.functions[0]
        assert bm25_fn.name == "bm25"
        assert bm25_fn.type == FunctionType.BM25
        assert bm25_fn.input_field_names == ["chunk_text"]
        assert bm25_fn.output_field_names == ["sparse_vector"]

    def test_collection_name_and_partitions(self) -> None:
        mock_client = MagicMock()
        mock_client.prepare_index_params.return_value = MagicMock()

        create_knowledge_chunks_collection(client=mock_client)

        call_kwargs = mock_client.create_collection.call_args.kwargs
        assert call_kwargs["collection_name"] == COLLECTION_NAME
        assert call_kwargs["num_partitions"] == 64

    def test_indexes_created(self) -> None:
        mock_client = MagicMock()
        mock_index_params = MagicMock()
        mock_client.prepare_index_params.return_value = mock_index_params

        create_knowledge_chunks_collection(client=mock_client)

        calls = mock_index_params.add_index.call_args_list
        assert len(calls) == 2

        # HNSW on dense_vector
        dense_call = calls[0]
        assert dense_call.kwargs["field_name"] == "dense_vector"
        assert dense_call.kwargs["index_type"] == "HNSW"
        assert dense_call.kwargs["metric_type"] == "COSINE"
        assert dense_call.kwargs["params"] == {"M": 16, "efConstruction": 200}

        # SPARSE_INVERTED_INDEX on sparse_vector
        sparse_call = calls[1]
        assert sparse_call.kwargs["field_name"] == "sparse_vector"
        assert sparse_call.kwargs["index_type"] == "SPARSE_INVERTED_INDEX"
        assert sparse_call.kwargs["metric_type"] == "BM25"
