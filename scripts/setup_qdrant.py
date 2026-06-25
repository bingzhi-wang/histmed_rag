# scripts/setup_qdrant.py
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PayloadSchemaType,
    CreateAliasOperation, OptimizersConfigDiff
)

client = QdrantClient(host='localhost', port=6333)
COLLECTION = 'histmed_corpus'

# Delete collection if it exists (for clean setup)
if client.collection_exists(COLLECTION):
    client.delete_collection(COLLECTION)
    print(f'Deleted existing collection: {COLLECTION}')

# Create collection
# BGE-M3 dense vectors are 1024-dimensional
client.create_collection(
    collection_name=COLLECTION,
    vectors_config=VectorParams(
        size=1024,
        distance=Distance.COSINE
    ),
    optimizers_config=OptimizersConfigDiff(
        indexing_threshold=10000  # Start indexing after 10k vectors
    )
)

# Create payload indexes for fast metadata filtering
# This allows queries like: 'only return chunks from zh-classical'
for field, schema in [
    ('language',    PayloadSchemaType.KEYWORD),
    ('tradition',   PayloadSchemaType.KEYWORD),
    ('date_approx', PayloadSchemaType.INTEGER),
    ('source_text', PayloadSchemaType.KEYWORD),
    ('chapter_num', PayloadSchemaType.INTEGER),
]:
    client.create_payload_index(
        collection_name=COLLECTION,
        field_name=field,
        field_schema=schema
    )
    print(f'Created index on field: {field}')

info = client.get_collection(COLLECTION)
print(f'Collection created: {COLLECTION}')
print(f'Vector size: {info.config.params.vectors.size}')
