from requests import Response

class ApiError(Exception):
    """Custom exception for API errors."""

    def __init__(self, message: str = "API error occurred", status_code: int = None, response: Response = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response
