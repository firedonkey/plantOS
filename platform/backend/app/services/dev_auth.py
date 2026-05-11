from itsdangerous import BadSignature, URLSafeSerializer

from app.core.settings import Settings


TOKEN_SALT = "plantlab-dev-token-auth"


def issue_dev_token(settings: Settings, user_id: int) -> str:
    serializer = URLSafeSerializer(settings.session_secret, salt=TOKEN_SALT)
    return serializer.dumps({"user_id": user_id, "mode": "dev"})


def read_dev_token(settings: Settings, token: str) -> int | None:
    serializer = URLSafeSerializer(settings.session_secret, salt=TOKEN_SALT)
    try:
        payload = serializer.loads(token)
    except BadSignature:
        return None

    user_id = payload.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        return None
    return user_id
