class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 400, error_code: str = "AUTH_ERROR"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class UserAlreadyExistsError(AuthError):
    def __init__(self, message: str = "User with this email or username already exists"):
        super().__init__(message=message, status_code=409, error_code="USER_ALREADY_EXISTS")


class UserNotFoundError(AuthError):
    def __init__(self, message: str = "User not found"):
        super().__init__(message=message, status_code=404, error_code="USER_NOT_FOUND")


class InvalidCredentialsError(AuthError):
    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message=message, status_code=401, error_code="INVALID_CREDENTIALS")


class AccountLockedError(AuthError):
    def __init__(self, message: str = "Account is temporarily locked due to multiple failed login attempts"):
        super().__init__(message=message, status_code=423, error_code="ACCOUNT_LOCKED")


class AccountSuspendedError(AuthError):
    def __init__(self, message: str = "Account is suspended"):
        super().__init__(message=message, status_code=403, error_code="ACCOUNT_SUSPENDED")


class InvalidTokenError(AuthError):
    def __init__(self, message: str = "Invalid authentication token"):
        super().__init__(message=message, status_code=401, error_code="INVALID_TOKEN")


class TokenExpiredError(AuthError):
    def __init__(self, message: str = "Authentication token has expired"):
        super().__init__(message=message, status_code=401, error_code="TOKEN_EXPIRED")


class SessionRevokedError(AuthError):
    def __init__(self, message: str = "Session has been revoked or expired"):
        super().__init__(message=message, status_code=401, error_code="SESSION_REVOKED")


class SessionNotFoundError(AuthError):
    def __init__(self, message: str = "Session not found"):
        super().__init__(message=message, status_code=404, error_code="SESSION_NOT_FOUND")


class InsufficientPermissionsError(AuthError):
    def __init__(self, message: str = "Insufficient permissions to perform this action"):
        super().__init__(message=message, status_code=403, error_code="INSUFFICIENT_PERMISSIONS")


class WeakPasswordError(AuthError):
    def __init__(self, message: str = "Password does not meet complexity requirements"):
        super().__init__(message=message, status_code=422, error_code="WEAK_PASSWORD")


class InvalidApiKeyError(AuthError):
    def __init__(self, message: str = "Invalid or revoked API key"):
        super().__init__(message=message, status_code=401, error_code="INVALID_API_KEY")


class RateLimitExceededError(AuthError):
    def __init__(self, message: str = "Too many requests, please try again later"):
        super().__init__(message=message, status_code=429, error_code="RATE_LIMIT_EXCEEDED")
