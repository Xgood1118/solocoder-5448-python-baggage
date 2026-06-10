import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PORT: int = int(os.getenv("PORT", 8000))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    ENV: str = os.getenv("ENV", "development")

    LOST_THRESHOLD_MINUTES: int = int(os.getenv("LOST_THRESHOLD_MINUTES", 30))
    DELAY_DOMESTIC_HOURS: int = int(os.getenv("DELAY_DOMESTIC_HOURS", 4))
    DELAY_INTL_HOURS: int = int(os.getenv("DELAY_INTL_HOURS", 6))
    MONTREAL_CONVENTION_LIMIT_SDR: float = float(os.getenv("MONTREAL_CONVENTION_LIMIT_SDR", 1288))


settings = Settings()
