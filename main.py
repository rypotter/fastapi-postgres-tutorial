from typing import List
import databases
import sqlalchemy
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, BaseSettings
import os
import urllib

from dotenv_settings_handler import BaseSettingsHandler
from dotenv import load_dotenv

load_dotenv()

# https://pydantic-docs.helpmanual.io/usage/settings/#dotenv-env-support
# https://fastapi.tiangolo.com/advanced/settings/
# from functools import lru_cache
# from fastapi import Depends, FastAPI
# from . import config
# app = FastAPI()
# @lru_cache()
# def get_settings():
#     return config.Settings()
# @app.get("/info")
# async def info(settings: config.Settings = Depends(get_settings)):
#     return {
#         "app_name": settings.app_name,
#         "admin_email": settings.admin_email,
#         "items_per_user": settings.items_per_user,
#     }

class DbSettings(BaseSettingsHandler):
    host = "127.0.0.1"
    port = 5432
    usr: str
    pwd: str
    db: str


dbs = DbSettings()

db_url = f'postgresql://{dbs.usr}:{dbs.pwd}@{dbs.host}:{dbs.port}/{dbs.db}'
# print(DATABASE_URL)

# #
# # from functools import lru_cache
#
# @lru_cache()
# def get_settings():
#     return config.Settings()
#

database = databases.Database(db_url)

metadata = sqlalchemy.MetaData()

notes = sqlalchemy.Table(
    "notes",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("text", sqlalchemy.String),
    sqlalchemy.Column("completed", sqlalchemy.Boolean),
)

engine = sqlalchemy.create_engine(
    db_url, pool_size=3, max_overflow=0
)
metadata.create_all(engine)


class NoteIn(BaseModel):
    text: str
    completed: bool


class Note(BaseModel):
    id: int
    text: str
    completed: bool


app = FastAPI(title="REST API using FastAPI PostgreSQL Async EndPoints")
# https://fastapi.tiangolo.com/tutorial/cors/
# allow_origins=['client-facing-example-app.com', 'localhost:5000']
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# https://fastapi.tiangolo.com/advanced/events/
@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.post("/notes/", response_model=Note, status_code=status.HTTP_201_CREATED)
async def create_note(note: NoteIn):
    query = notes.insert().values(text=note.text, completed=note.completed)
    last_record_id = await database.execute(query)
    return {**note.dict(), "id": last_record_id}


@app.put("/notes/{note_id}/", response_model=Note, status_code=status.HTTP_200_OK)
async def update_note(note_id: int, payload: NoteIn):
    query = notes.update().where(notes.c.id == note_id).values(text=payload.text, completed=payload.completed)
    await database.execute(query)
    return {**payload.dict(), "id": note_id}


# paginated list
@app.get("/notes/", response_model=List[Note], status_code=status.HTTP_200_OK)
async def read_notes(skip: int = 0, take: int = 20):
    query = notes.select().offset(skip).limit(take)
    return await database.fetch_all(query)


@app.get("/notes/{note_id}/", response_model=Note, status_code=status.HTTP_200_OK)
async def read_notes(note_id: int):
    query = notes.select().where(notes.c.id == note_id)
    return await database.fetch_one(query)


@app.delete("/notes/{note_id}/", status_code=status.HTTP_200_OK)
async def update_note(note_id: int):
    query = notes.delete().where(notes.c.id == note_id)
    await database.execute(query)
    return {"message": "Note with id: {} deleted successfully!".format(note_id)}
