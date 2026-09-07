from fastapi import APIRouter

router = APIRouter()


@router.get("/impact")
def impact():
    return {"impact": "placeholder metrics"}
