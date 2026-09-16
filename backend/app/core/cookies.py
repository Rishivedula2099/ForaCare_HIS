from fastapi import Response

from app.core.config import Settings

ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"


def set_auth_cookies(
    response: Response,
    *,
    settings: Settings,
    access_token: str,
    refresh_token: str,
    access_max_age: int,
    refresh_max_age: int,
) -> None:
    common = dict(
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.session_cookie_samesite,
        domain=settings.cookie_domain,
        path="/",
    )
    response.set_cookie(ACCESS_COOKIE_NAME, access_token, max_age=access_max_age, **common)
    response.set_cookie(REFRESH_COOKIE_NAME, refresh_token, max_age=refresh_max_age, **common)


def clear_auth_cookies(response: Response, *, settings: Settings) -> None:
    common = dict(
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.session_cookie_samesite,
        domain=settings.cookie_domain,
        path="/",
    )
    response.delete_cookie(ACCESS_COOKIE_NAME, **common)
    response.delete_cookie(REFRESH_COOKIE_NAME, **common)
