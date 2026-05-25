import logging
from fastapi import APIRouter, HTTPException, Depends

from models.health import BiometricReading
from services import firebase, claude
from services.auth import verify_token

logger = logging.getLogger(__name__)
router = APIRouter()

MIN_READINGS_FOR_ANALYSIS = 10


@router.post("/biometrics")
async def save_biometric(reading: BiometricReading, user_id: str = Depends(verify_token)):
    doc_id = firebase.save_biometric(user_id, reading.model_dump(exclude={"user_id"}))
    return {"id": doc_id}


@router.get("/biometrics")
async def get_biometrics(limit: int = 500, user_id: str = Depends(verify_token)):
    return firebase.get_biometrics(user_id, limit)


@router.get("/energy")
async def get_energy_profile(user_id: str = Depends(verify_token)):
    history = firebase.get_biometrics(user_id, limit=500)

    if len(history) < MIN_READINGS_FOR_ANALYSIS:
        return {
            "error": "not enough data yet",
            "readings": len(history),
            "needed": MIN_READINGS_FOR_ANALYSIS,
        }

    try:
        profile = claude.analyze_energy_patterns(history)
    except Exception as e:
        logger.error("Energy analysis failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=502, detail="Energy analysis failed")

    firebase.db().collection("energy_profiles").document(user_id).set(profile)
    return profile


@router.get("/state")
async def get_current_state(user_id: str = Depends(verify_token)):
    readings = firebase.get_biometrics(user_id, limit=3)

    if not readings:
        return {"state": "unknown"}

    latest = readings[0]
    hr = latest.get("heart_rate") or 0
    hrv = latest.get("hrv") or 0

    if hrv > 60 and hr < 80:
        state = "focused"
    elif hrv < 30 or hr > 100:
        state = "stressed"
    elif hr < 60:
        state = "resting"
    else:
        state = "normal"

    return {"state": state, "heart_rate": hr, "hrv": hrv}
