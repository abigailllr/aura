import logging
from firebase_admin import messaging

logger = logging.getLogger(__name__)


def send(fcm_token: str, title: str, body: str):
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        token=fcm_token,
    )
    messaging.send(message)
