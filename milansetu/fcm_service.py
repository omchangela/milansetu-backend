"""
fcm_service.py — Firebase Cloud Messaging via Admin SDK HTTP v1 API.

Setup:
  1. pip install firebase-admin
  2. Download service account JSON from:
     Firebase Console → Project Settings → Service Accounts → Generate New Private Key
  3. Save it as backend/serviceAccountKey.json

Usage:
  from milansetu.fcm_service import send_push
  send_push(user, "New Message", "Priya sent you a message", data={"type": "chat"})
"""

import os
import logging

logger = logging.getLogger(__name__)

# Service account path — place your downloaded JSON here
SERVICE_ACCOUNT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'serviceAccountKey.json'
)

_firebase_app = None


def _get_firebase_app():
    """Lazy-init Firebase Admin SDK. Returns None if not configured."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    service_account_info = None
    env_creds = os.environ.get('FIREBASE_SERVICE_ACCOUNT', '').strip()
    if env_creds:
        try:
            import json
            service_account_info = json.loads(env_creds)
        except Exception as e:
            logger.error("[FCM] Failed to parse FIREBASE_SERVICE_ACCOUNT environment variable: %s", e)

    if not service_account_info and os.path.exists(SERVICE_ACCOUNT_PATH):
        service_account_info = SERVICE_ACCOUNT_PATH

    if not service_account_info:
        logger.warning(
            "[FCM] serviceAccountKey.json not found at %s and FIREBASE_SERVICE_ACCOUNT env var is empty. "
            "Push notifications will be disabled.",
            SERVICE_ACCOUNT_PATH
        )
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            cred = credentials.Certificate(service_account_info)
            _firebase_app = firebase_admin.initialize_app(cred)
        else:
            _firebase_app = firebase_admin.get_app()

        return _firebase_app
    except ImportError:
        logger.warning(
            "[FCM] firebase-admin is not installed. "
            "Run: pip install firebase-admin"
        )
        return None
    except Exception as exc:
        logger.error("[FCM] Failed to init Firebase Admin SDK: %s", exc)
        return None



def send_push(to_user, title: str, body: str, data: dict = None) -> bool:
    """
    Send an FCM push notification to a specific user.

    Args:
        to_user: Django User instance (must have an fcm_token related object)
        title:   Notification title
        body:    Notification body text
        data:    Optional dict of string key/value pairs for the data payload

    Returns:
        True if sent successfully, False otherwise.
    """
    app = _get_firebase_app()
    if app is None:
        return False

    try:
        from milansetu.models import FCMToken
        fcm_record = FCMToken.objects.filter(user=to_user).first()
        if not fcm_record or not fcm_record.token:
            logger.debug("[FCM] No FCM token for user %s", to_user.id)
            return False

        from firebase_admin import messaging

        # All data values must be strings for FCM
        str_data = {k: str(v) for k, v in (data or {}).items()}

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=str_data,
            token=fcm_record.token,
            android=messaging.AndroidConfig(priority='high'),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound='default')
                )
            ),
            webpush=messaging.WebpushConfig(
                notification=messaging.WebpushNotification(
                    title=title,
                    body=body,
                    icon='/milansetu-icon.png',
                )
            ),
        )

        response = messaging.send(message)
        logger.info("[FCM] Sent to user %s — message ID: %s", to_user.id, response)
        return True

    except Exception as exc:
        logger.error("[FCM] Failed to send to user %s: %s", to_user.id, exc)
        return False


def send_interest_notification(sender, receiver):
    """
    Notify receiver that sender sent them an interest.
    Called from SentInterestListView.post()
    """
    sender_name = getattr(sender, 'profile', None)
    if sender_name:
        sender_name = sender_name.full_name or sender.email
    else:
        sender_name = sender.email

    return send_push(
        to_user=receiver,
        title="New Interest Request!",
        body=f"{sender_name} is interested in your profile. Check it out!",
        data={"type": "interest", "sender_id": str(sender.id), "url": "/milansetu/#notifications"},
    )


def send_message_notification(sender, receiver, preview: str = ""):
    """
    Notify receiver of a new chat message from sender.
    """
    sender_name = getattr(sender, 'profile', None)
    sender_name = (sender_name.full_name if sender_name else None) or sender.email

    body = f"{sender_name}: {preview[:80]}" if preview else f"New message from {sender_name}"
    return send_push(
        to_user=receiver,
        title="New Message on MilanSetu",
        body=body,
        data={"type": "message", "sender_id": str(sender.id), "url": "/milansetu/#messages"},
    )


def send_interest_accepted_notification(sender, receiver):
    """
    Notify receiver (original sender of the interest) that sender (original receiver)
    accepted their interest request.
    """
    sender_name = getattr(sender, 'profile', None)
    if sender_name:
        sender_name = sender_name.full_name or sender.email
    else:
        sender_name = sender.email

    return send_push(
        to_user=receiver,
        title="Interest Accepted!",
        body=f"{sender_name} accepted your interest request! You can now start chatting.",
        data={"type": "interest_accepted", "sender_id": str(sender.id), "url": "/milansetu/#messages"},
    )

