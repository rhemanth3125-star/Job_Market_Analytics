from functools import lru_cache

from pymongo import MongoClient

from config import Config


@lru_cache(maxsize=1)
def get_mongo_client() -> MongoClient:
    return MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000, tz_aware=True)


def get_predictions_collection():
    return get_mongo_client()[Config.DATABASE_NAME]["salary_predictions"]
