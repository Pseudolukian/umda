from pydantic import BaseModel, Field

class MediaYml(BaseModel):
    name: str = Field(..., description="The name of the media item.")
    url: str = Field(..., description="The URL where the media item can be accessed.")
    type: str = Field(..., description="The type of media (e.g., image, video, audio).")
    description: str = Field(None, description="A brief description of the media item.")