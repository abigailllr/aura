import logging
from datetime import datetime, timezone, timedelta

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


def delete_conversation(user_id: str, conversation_id: str) -> bool:
    ref = db().collection("conversations").document(conversation_id)
    doc = ref.get()
    if not doc.exists or doc.to_dict().get("user_id") != user_id:
        return False
    ref.delete()
    return True


def save_energy_profile(user_id: str, profile: dict):
    db().collection("energy_profiles").document(user_id).set(profile)


def get_energy_profile(user_id: str) -> dict | None:
    doc = db().collection("energy_profiles").document(user_id).get()
    return doc.to_dict() if doc.exists else None


def upload_photo(user_id: str, image_bytes: bytes, person_id: str) -> str:
    blob = bucket().blob(f"people/{user_id}/{person_id}.jpg")
    blob.upload_from_string(image_bytes, content_type="image/jpeg")
    blob.make_public()
    return blob.public_url


def save_fcm_token(user_id: str, token: str):
    db().collection("fcm_tokens").document(user_id).set({"token": token})


def get_fcm_token(user_id: str) -> str | None:
    doc = db().collection("fcm_tokens").document(user_id).get()
    return doc.to_dict().get("token") if doc.exists else None


def get_active_user_ids(since_hours: int = 24) -> list[str]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    docs = (
        db().collection("biometrics")
        .where("recorded_at", ">=", cutoff)
        .stream()
    )
    seen: set[str] = set()
    result = []
    for d in docs:
        uid = d.to_dict().get("user_id")
        if uid and uid not in seen:
            seen.add(uid)
            result.append(uid)
    return result


def save_insight(user_id: str, text: str):
    db().collection("insights").document().set({
        "user_id": user_id,
        "text": text,
        "read": False,
        "created_at": firestore.SERVER_TIMESTAMP,
    })


def get_unread_insights(user_id: str) -> list[dict]:
    docs = (
        db().collection("insights")
        .where("user_id", "==", user_id)
        .where("read", "==", False)
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .stream()
    )
    return [{"id": d.id, **d.to_dict()} for d in docs]


def mark_insights_read(user_id: str):
    docs = (
        db().collection("insights")
        .where("user_id", "==", user_id)
        .where("read", "==", False)
        .stream()
    )
    for d in docs:
        d.reference.update({"read": True})
