from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    recipient_count: int = Field(ge=1)
    created_at: datetime