from pydantic import BaseModel, Field
from typing_extensions import Annotated

# Classification Service
PngPath = Annotated[str, Field(pattern=r".+\.png$")]


class ClassificationRequest(BaseModel):
    object_id: int
    image_path: PngPath


def sanitize_classification_request(untrusted_json_string: str):
    return ClassificationRequest.model_validate_json(untrusted_json_string)
