from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class ClientsHttpConfig:
    SCHEMA: str = "https"
    BASE_URL: str = getenv("BASE_URL")
    PORT: str = getenv("PORT", "")
    VERIFY: str | bool = getenv("VERIFY_SSL_CERTIFICATE", False)
    CERT: str = getenv("CERTIFICATE_PATH", None)
    MAX_RESPONSE_TIME: int = 10
    TIMEOUT: int = 10
