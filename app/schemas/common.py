"""Shared API schemas."""

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """Base for schemas built from ORM objects."""

    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    detail: str
