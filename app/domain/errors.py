from app.domain.models import ErrorCode


class ParkingError(Exception):
    def __init__(self, error_code: ErrorCode, message: str):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
