import logging
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth

logger = logging.getLogger(__name__)

bearer = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Security(bearer)) -> str:
    try:
        decoded = auth.verify_id_token(credentials.credentials)
        return decoded["uid"]
    except auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="token expired")
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="invalid token")
    except Exception as e:
        logger.error("Auth error: %s", e)
        raise HTTPException(status_code=401, detail="unauthorized")
