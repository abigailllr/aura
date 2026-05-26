import asyncio
import base64
import logging
from fastapi import APIRouter, HTTPException, Depends
from firebase_admin import firestore
from pydantic import BaseModel

from models.person import Person
from services import firebase, pinecone_client, claude
from services.auth import verify_token

logger = logging.getLogger(__name__)
router = APIRouter()


class FaceScanRequest(BaseModel):
    image_base64: str
    context: str | None = None


@router.post("/save")
async def save_person(person: Person, user_id: str = Depends(verify_token)):
    person_id = await asyncio.to_thread(
        firebase.save_person, user_id, person.model_dump(exclude={"id", "user_id"})
    )
    return {"id": person_id}


@router.post("/scan")
async def scan_face(req: FaceScanRequest, user_id: str = Depends(verify_token)):
    person_id = await asyncio.to_thread(pinecone_client.find_face, user_id, req.image_base64)

    if not person_id:
        return {"known": False}

    people = await asyncio.to_thread(firebase.get_people, user_id)
    person = next((p for p in people if p["id"] == person_id), None)

    if not person:
        return {"known": False}

    await asyncio.to_thread(firebase.update_person, person_id, {"last_seen": firestore.SERVER_TIMESTAMP})
    notes = person.get("notes", "")
    whisper_text = f"{person['name']}. {notes}".strip().rstrip(".")

    return {"known": True, "person": person, "whisper": whisper_text}


@router.post("/introduce")
async def introduce_person(req: FaceScanRequest, user_id: str = Depends(verify_token)):
    if not req.context:
        raise HTTPException(status_code=422, detail="context is required")

    context = await asyncio.to_thread(claude.extract_person_context, req.context)

    person_id = await asyncio.to_thread(firebase.save_person, user_id, {
        "name": context.name,
        "notes": context.notes,
        "job": context.job,
        "company": context.company,
    })

    if req.image_base64:
        try:
            await asyncio.to_thread(pinecone_client.upsert_face, person_id, user_id, req.image_base64)
            image_bytes = base64.b64decode(req.image_base64)
            photo_url = await asyncio.to_thread(firebase.upload_photo, user_id, image_bytes, person_id)
            await asyncio.to_thread(firebase.update_person, person_id, {
                "photo_url": photo_url,
                "face_embedding_id": person_id,
            })
        except Exception as e:
            logger.error("Face indexing failed for %s: %s", person_id, e)

    return {"id": person_id, "name": context.name}


@router.get("/")
async def get_people(user_id: str = Depends(verify_token)):
    return await asyncio.to_thread(firebase.get_people, user_id)


@router.get("/relationships")
async def get_relationship_insights(user_id: str = Depends(verify_token)):
    people = await asyncio.to_thread(firebase.get_people, user_id)

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

    try:
        insight = await asyncio.to_thread(claude.analyze_relationships, timeline)
    except Exception as e:
        logger.error("Relationship analysis failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=502, detail="Relationship analysis failed")

    return {"insight": insight, "people": people}
