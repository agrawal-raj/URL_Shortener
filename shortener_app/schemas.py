from pydantic import BaseModel

class URLBase(BaseModel):
    target_url: str

class URL(URLBase):
    is_active: bool
    clicks: int

    class Config:
        from_attributes = True

class URLInfo(URL):
    url: str
    admin_url: str

    