from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.api.deps import AppSettings
from app.services.errors import NotFound

router = APIRouter(prefix="/samples", tags=["samples"])

# Allowlist: the name is never joined into a path unless it is one of these.
SAMPLES = {
    "checking_simple.csv": "text/csv",
    "credit_card.csv": "text/csv",
    "bank_messy.csv": "text/csv",
    "credit_card.xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


@router.get("/{name}")
def get_sample(name: str, settings: AppSettings) -> FileResponse:
    path = settings.samples_dir / name
    if name not in SAMPLES or not path.is_file():
        raise NotFound(f"no sample named {name!r}")
    return FileResponse(path, media_type=SAMPLES[name], filename=name)
