from fastapi import HTTPException


def api_error(status_code: int, code: str, message: str, meta: dict | None = None) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message,
            "meta": meta or {},
        },
    )
