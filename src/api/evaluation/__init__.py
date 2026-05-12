from fastapi import Request
from fastapi import APIRouter, Depends
from src.security.o_auth import auth_dependency
from src.services.ragas_service import ragas_evaluation_service
from src.schema.evaluation_schema import EvaluateSingleRequest, EvaluateBatchRequest
from src.utils.limiter import limiter

router = APIRouter(prefix="/evaluate", tags=["Evaluation"])


@router.post("/single")
@limiter.limit("5/minute")
async def evaluate_single(
    request: Request,
    body: EvaluateSingleRequest,
    current_user=Depends(auth_dependency.get_current_active_user),
):

    result = await ragas_evaluation_service.evaluate_single(
        query=body.query,
        ground_truth=body.ground_truth,
        user_id=current_user.id,
    )
    return {"success": True, "data": result}


@router.post("/batch")
@limiter.limit("2/minute")
async def evaluate_batch(
    request: Request,
    body: EvaluateBatchRequest,
    current_user=Depends(auth_dependency.get_current_active_user),
):

    samples = [s.model_dump() for s in body.samples]
    result = await ragas_evaluation_service.evaluate_batch(
        samples=samples,
        user_id=current_user.id,
    )
    return {"success": True, "data": result}