from fastapi.responses import JSONResponse
from constants.clinic_status import STATUS

def success_response(data: dict, status_code: int = 200):
    """
    Standard success response
    """
    return JSONResponse(
        content={"status": STATUS["SUCCESS"], "data": data},
        status_code=status_code
    )

def error_response(message: str, status_code: int = 400):
    """
    Standard error response
    """
    return JSONResponse(
        content={"status": STATUS["ERROR"], "message": message},
        status_code=status_code
    )
