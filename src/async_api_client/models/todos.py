from pydantic import BaseModel, Field


class Todo(BaseModel):
    id: int
    user_id: int = Field(alias="userId")
    title: str
    completed: bool

    model_config = {"populate_by_name": True}
