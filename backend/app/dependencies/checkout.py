from fastapi import HTTPException

from app.config import settings

CHECKOUT_UNAVAILABLE = (
    "Checkout is temporarily unavailable. You can still browse and save your cart."
)


def require_checkout_enabled() -> None:
    if not settings.checkout_enabled:
        raise HTTPException(status_code=503, detail=CHECKOUT_UNAVAILABLE,
                            headers={"Cache-Control": "no-store"})
