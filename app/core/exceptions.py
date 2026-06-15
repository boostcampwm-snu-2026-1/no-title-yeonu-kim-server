from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorCode:
    http_status: int
    code: str
    message: str


class AppException(Exception):
    def __init__(self, error: ErrorCode) -> None:
        super().__init__(error.message)
        self.status_code = error.http_status
        self.code = error.code
        self.message = error.message


# Auth
AUTH_001 = ErrorCode(401, "AUTH_001", "Authorization header is missing or malformed")
AUTH_002 = ErrorCode(401, "AUTH_002", "Invalid credentials")
AUTH_007 = ErrorCode(
    403, "AUTH_007", "You do not have permission to perform this action"
)

# User
USER_001 = ErrorCode(409, "USER_001", "This email is already registered")
USER_002 = ErrorCode(404, "USER_002", "User not found")
USER_006 = ErrorCode(400, "USER_006", "Email verification code is invalid or expired")

# Mail
MAIL_001 = ErrorCode(500, "MAIL_001", "Failed to send email")

# Store
STORE_001 = ErrorCode(404, "STORE_001", "Store not found")

# Event
EVENT_001 = ErrorCode(404, "EVENT_001", "Event not found")

# Application
APPLICATION_001 = ErrorCode(
    403, "APPLICATION_001", "You are not allowed to access this application"
)
APPLICATION_002 = ErrorCode(404, "APPLICATION_002", "Application not found")
APPLICATION_003_APPLY = ErrorCode(
    409, "APPLICATION_003", "You have already applied for this event"
)
APPLICATION_003_SUBMIT = ErrorCode(
    409, "APPLICATION_003", "Review has already been submitted for this application"
)

# Deposit
DEPOSIT_001 = ErrorCode(400, "DEPOSIT_001", "Deposit balance is insufficient")
DEPOSIT_002 = ErrorCode(404, "DEPOSIT_002", "Deposit record not found")

# General
GEN_003_CLOSED = ErrorCode(400, "GEN_003", "Event is already closed")
GEN_003_AMOUNT = ErrorCode(400, "GEN_003", "Amount must be a positive number")
GEN_003_STATUS = ErrorCode(
    400, "GEN_003", "Application cannot be cancelled in its current status"
)
GEN_005 = ErrorCode(400, "GEN_005", "Invalid wallet address format")

# Image (server-side only, not in mock)
IMAGE_001 = ErrorCode(422, "IMAGE_001", "Image does not meet the event conditions")
IMAGE_002 = ErrorCode(400, "IMAGE_002", "Image not found or inaccessible")


class ImageConditionNotMetError(AppException):
    def __init__(self) -> None:
        super().__init__(IMAGE_001)
