from fastapi import APIRouter

router = APIRouter(tags=["Ejemplo"], prefix="/ejemplo")

@router.get("/")
def read_ejemplo():
    return {"message": "Ejemplo endpoint"}
