from pydantic import BaseModel, Field, EmailStr


class PostCreate(BaseModel):
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    user_id: int = Field(alias="userId", ge=1)

    model_config = {"populate_by_name": True}


class Post(BaseModel):
    id: int
    user_id: int = Field(alias="userId")
    title: str
    body: str

    model_config = {"populate_by_name": True}


class Comment(BaseModel):
    id: int
    post_id: int = Field(alias="postId")
    name: str
    email: EmailStr
    body: str

    model_config = {"populate_by_name": True}
