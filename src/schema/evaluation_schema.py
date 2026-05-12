from pydantic import BaseModel, Field

class EvaluateSingleRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The question to evaluate")
    ground_truth: str = Field(..., min_length=1, description="The expected correct answer")


class EvaluateBatchRequest(BaseModel):
    samples: list[EvaluateSingleRequest] = Field(
        ..., min_length=1, max_length=20,
        description="List of query + ground_truth pairs (max 20)"
    )