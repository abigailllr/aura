import base64
import numpy as np
from pinecone import Pinecone

from config import settings

_index = None


def _init():
    global _index
    if _index is None:
        pc = Pinecone(api_key=settings.pinecone_api_key)
        _index = pc.Index(settings.pinecone_index)


def image_to_embedding(image_base64: str) -> list[float]:
    image_bytes = base64.b64decode(image_base64)
    arr = np.frombuffer(image_bytes[:512], dtype=np.uint8).astype(np.float32)
    arr = arr / 255.0
    if len(arr) < 512:
        arr = np.pad(arr, (0, 512 - len(arr)))
    return arr.tolist()


def upsert_face(person_id: str, user_id: str, image_base64: str):
    _init()
    embedding = image_to_embedding(image_base64)
    _index.upsert(vectors=[{
        "id": person_id,
        "values": embedding,
        "metadata": {"user_id": user_id, "person_id": person_id},
    }])


def find_face(user_id: str, image_base64: str, threshold: float = 0.85) -> str | None:
    _init()
    embedding = image_to_embedding(image_base64)
    results = _index.query(
        vector=embedding,
        top_k=1,
        filter={"user_id": {"$eq": user_id}},
        include_metadata=True,
    )
    if not results.matches:
        return None
    top = results.matches[0]
    if top.score >= threshold:
        return top.metadata["person_id"]
    return None
