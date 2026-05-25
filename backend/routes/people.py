import base64
import logging
from fastapi import APIRouter, HTTPException
from firebase_admin import firestore

from models.person import Person, FaceScanRequest
from services import firebase, pinecone_client, claude

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/save")
async def save_person(person: Person):
    person_id = firebase.save_person(person.user_id, person.model_dump(exclude={"id"}))
    return {"id": person_id}


@router.post("/scan")
async def scan_face(req: FaceScanRequest):
    person_id = pinecone_client.find_face(req.user_id, req.image_base64)

    if not person_id:
        return {"known": False}

    people = firebase.get_people(req.user_id)
    person = next((p for p in people if p["id"] == person_id), None)

    if not person:
        return {"known": False}

    firebase.update_person(person_id, {"last_seen": firestore.SERVER_TIMESTAMP})

    notes = person.get("notes", "")
    whisper_text = f"{person['name']}. {notes}".strip().rstrip(".")

    return {"known": True, "person": person, "whisper": whisper_text}


@router.post("/introduce")
async def introduce_person(req: FaceScanRequest):
    if not req.context:
        raise HTTPException(status_code=422, detail="context is required")

    context = claude.extract_person_context(req.context)

    person_id = firebase.save_person(req.user_id, {
        "name": context.name,
        "notes": context.notes,
        "job": context.job,
        "company": context.company,
    })

    if req.image_base64:
        try:
            pinecone_client.upsert_face(person_id, req.user_id, req.image_base64)
            image_bytes = base64.b64decode(req.image_base64)
            photo_url = firebase.upload_photo(req.user_id, image_bytes, person_id)
            firebase.update_person(person_id, {
                "photo_url": photo_url,
                "face_embedding_id": person_id,
            })
        except Exception as e:
            logger.error("Face indexing failed for %s: %s", person_id, e)

    return {"id": person_id, "name": context.name}


@router.get("/{user_id}")
async def get_people(user_id: str):
    return firebase.get_people(user_id)


@router.get("/{user_id}/relationships")
async def get_relationship_insights(user_id: str):
    people = firebase.get_people(user_id)

    if not people:
        return {"insight": "No people saved yet.", "people": []}

    timeline = [
        {
            "person": p["name"],
            "last_seen": str(p.get("last_seen")),
            "notes": p.get("notes"),
            "job": p.get("job"),
        }
        for p in people
    ]

    insight = claude.analyze_relationships(timeline)
    return {"insight": insight, "people": people}
