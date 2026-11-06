import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _project_path(environment_name: str, default_name: str) -> Path:
    value = Path(os.getenv(environment_name, default_name)).expanduser()
    return value if value.is_absolute() else BASE_DIR / value


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "local-job-market-analytics")
    DATASET_PATH = _project_path("DATASET_PATH", "cleaned_job_market_dataset.csv")
    MODEL_PATH = _project_path("MODEL_PATH", "final_salary_prediction_model.pkl")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "job_market_analytics")
    MAX_CONTENT_LENGTH = 16 * 1024
