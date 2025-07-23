import pathlib

from pydantic import BaseModel, Field
from typing_extensions import Annotated

# Classification Service
ImagePath = Annotated[str, Field(pattern=r".+\.(?:png|jpg)$")]


class ClassificationRequest(BaseModel):
    object_id: int
    image_path: ImagePath


def sanitize_classification_request(untrusted_json_string: str):
    payload = ClassificationRequest.model_validate_json(untrusted_json_string)

    # validate image_path is child of sorter directory
    image_path = pathlib.Path(payload.image_path).resolve()
    sorter_path = pathlib.Path(__file__).parents[2]
    is_within = image_path.is_relative_to(sorter_path)
    if not is_within:
        raise Exception(f"Given image_path '{image_path}' is not a child of sorter dir")

    return payload
