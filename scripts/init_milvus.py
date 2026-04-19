"""Initialize Milvus collection for knowledge chunks.

Creates the knowledge_chunks collection with hybrid search support
(dense HNSW + sparse BM25). Idempotent — skips if collection exists.

Usage:
    python -m scripts.init_milvus
"""
from __future__ import annotations

import os

from pymilvus import MilvusClient

COLLECTION_NAME = "knowledge_chunks"


def init_collection() -> None:
    """Create knowledge_chunks collection if it doesn't exist."""
    uri = os.environ.get("MILVUS_URI", "http://localhost:19530")
    client = MilvusClient(uri=uri)

    if client.has_collection(COLLECTION_NAME):
        print(f"✅ Collection '{COLLECTION_NAME}' already exists, skipping.")
        return

    # Detect embedding dimension from env or default
    dim = int(os.environ.get("EMBEDDING_DIM", "4096"))

    from pymilvus import CollectionSchema, DataType, FieldSchema, Function, FunctionType

    schema = CollectionSchema(fields=[
        FieldSchema("id", DataType.VARCHAR, max_length=64, is_primary=True),
        FieldSchema("tenant_id", DataType.VARCHAR, max_length=64, is_partition_key=True),
        FieldSchema("doc_id", DataType.VARCHAR, max_length=64),
        FieldSchema(
            "chunk_text", DataType.VARCHAR, max_length=4096,
            enable_analyzer=True, analyzer_params={"type": "chinese"},
        ),
        FieldSchema("dense_vector", DataType.FLOAT_VECTOR, dim=dim),
        FieldSchema("sparse_vector", DataType.SPARSE_FLOAT_VECTOR),
        FieldSchema("created_at", DataType.INT64),
    ])

    bm25_function = Function(
        name="bm25", function_type=FunctionType.BM25,
        input_field_names=["chunk_text"], output_field_names=["sparse_vector"],
    )
    schema.add_function(bm25_function)

    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="dense_vector", index_type="HNSW",
        metric_type="COSINE", params={"M": 16, "efConstruction": 200},
    )
    index_params.add_index(
        field_name="sparse_vector", index_type="SPARSE_INVERTED_INDEX", metric_type="BM25",
    )

    client.create_collection(
        collection_name=COLLECTION_NAME, schema=schema,
        index_params=index_params, num_partitions=64,
    )
    print(f"✅ Collection '{COLLECTION_NAME}' created (dim={dim}, partitions=64)")


if __name__ == "__main__":
    init_collection()
