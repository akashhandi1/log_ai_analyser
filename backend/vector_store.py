import os
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from sentence_transformers import SentenceTransformer

# Initialize embedding model
encoder = SentenceTransformer("all-MiniLM-L6-v2")

# Initialize Local Qdrant
DB_PATH = os.path.join(os.path.dirname(__file__), "vector_db_data")
client = QdrantClient(path=DB_PATH)
COLLECTION_NAME = "log_incidents"

# Create collection if it doesn't exist
try:
    client.get_collection(collection_name=COLLECTION_NAME)
except Exception:
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )

def add_incident(log_message: str, root_cause: str, fix: str):
    """Saves a resolved incident to Qdrant."""
    vector = encoder.encode(log_message).tolist()
    point_id = str(uuid.uuid4())
    
    payload = {
        "log_message": log_message,
        "root_cause": root_cause,
        "fix": fix
    }
    
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
        ]
    )

def search_similar_incidents(log_message: str, score_threshold: float = 0.8):
    """Queries Qdrant for previously matched errors."""
    vector = encoder.encode(log_message).tolist()
    
    try:
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            limit=1
        ).points
        
        if results and results[0].score >= score_threshold:
            return results[0].payload
    except Exception as e:
        print(f"Error querying Qdrant: {e}")
    return None