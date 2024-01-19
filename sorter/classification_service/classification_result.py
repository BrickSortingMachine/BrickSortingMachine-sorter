from dataclasses import dataclass


@dataclass
class ClassificationResult:
    predicted_class: str
    probability: float
    uniqueness: float
    prediction_list: list
    label_data: dict
    predicted_class_high: str
    low_list: list
    high_list: list
