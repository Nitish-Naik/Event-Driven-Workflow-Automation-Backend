from pymongo import MongoClient

from app.config import settings


client = MongoClient(settings.mongodb_uri)

database = client[settings.mongodb_database]


def get_database():
    return database