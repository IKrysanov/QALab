from pydantic import BaseModel, EmailStr, Field


class GeoLocation(BaseModel):
    lat: str
    lng: str


class Address(BaseModel):
    street: str
    suite: str
    city: str
    zipcode: str
    geo: GeoLocation


class Company(BaseModel):
    name: str
    catch_phrase: str = Field(alias="catchPhrase")
    bs: str

    model_config = {"populate_by_name": True}


class User(BaseModel):
    id: int
    name: str
    username: str
    email: EmailStr
    address: Address
    phone: str
    website: str  # У JSONPlaceholder тут без http:// → не HttpUrl
    company: Company
