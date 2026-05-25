import logging
import firebase_admin
from firebase_admin import credentials, firestore, storage

from config import settings

logger = logging.getLogger(__name__)

_db = None
_bucket = None


def init_firebase():
    global _db, _bucket
    cred = credentials.Certificate(settings.firebase_credentials_path)
    app = firebase_admin.initialize_app(cred, {
        "storageBucket": settings.firebase_storage_bucket,
    })
    _db = firestore.client(app)
    _bucket = storage.bucket(app=app)
    logger.info("Firebase initialised")


def db() -> firestore.Client:
    return _db


def bucket():
    return _bucket


def save_conversation(user_id: str, messages: list[dict]) -> str:
    ref = db().collection("conversations").document()
    ref.set({
        "user_id": user_id,
        "messages": messages,
        "created_at": firestore.SERVER_TIMESTAMP,
    })
    return ref.id


def get_conversations(user_id: str, limit: int = 20) -> list[dict]:
    docs = (
        db().collection("conversations")
        .where("user_id", "==", user_id)
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [{"id": d.id, **d.to_dict()} for d in docs]


def save_person(user_id: str, person: dict) -> str:
    ref = db().collection("people").document()
    ref.set({
        "user_id": user_id,
        "created_at": firestore.SERVER_TIMESTAMP,
        **person,
    })
    return ref.id


def get_people(user_id: str) -> list[dict]:
    docs = (
        db().collection("people")
        .where("user_id", "==", user_id)
        .stream()
    )
    return [{"id": d.id, **d.to_dict()} for d in docs]


def update_person(person_id: str, data: dict):
    db().collection("people").document(person_id).update(data)


def save_biometric(user_id: str, reading: dict) -> str:
    ref = db().collection("biometrics").document()
    ref.set({
        "user_id": user_id,
        "recorded_at": firestore.SERVER_TIMESTAMP,
        **reading,
    })
    return ref.id


def get_biometrics(user_id: str, limit: int = 500) -> list[dict]:
    docs = (
        db().collection("biometrics")
        .where("user_id", "==", user_id)
        .order_by("recorded_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [d.to_dict() for d in docs]


def upload_photo(user_id: str, image_bytes: bytes, person_id: str) -> str:
    blob = bucket().blob(f"people/{user_id}/{person_id}.jpg")
    blob.upload_from_string(image_bytes, content_type="image/jpeg")
    blob.make_public()
    return blob.public_url
