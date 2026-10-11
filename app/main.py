from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.schemas import BatchResponse
from app.services import create_certificate_batch


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
DEFAULT_TEMPLATE = Path(__file__).resolve().parent.parent / "template.png"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Bulk Certificate Generator", version="1.0.0", lifespan=lifespan
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/certificates/generate",
    status_code=status.HTTP_200_OK,
    response_class=Response,
    responses={200: {"content": {"application/zip": {}}}},
)
async def generate_certificates(
    csv_file: UploadFile = File(..., description="UTF-8 CSV with a required name column"),
    template: UploadFile | None = File(default=None, description="Optional PNG or JPEG background"),
    db: Session = Depends(get_db),
) -> Response:
    if csv_file.size is not None and csv_file.size > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="CSV upload exceeds 10 MB.")
    csv_content = await csv_file.read(MAX_UPLOAD_BYTES + 1)
    if len(csv_content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="CSV upload exceeds 10 MB.")

    template_content = None
    if template is not None:
        if template.size is not None and template.size > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Template upload exceeds 10 MB.")
        template_content = await template.read(MAX_UPLOAD_BYTES + 1)
        if len(template_content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Template upload exceeds 10 MB.")
    elif DEFAULT_TEMPLATE.exists():
        template_content = DEFAULT_TEMPLATE.read_bytes()

    try:
        batch, archive = create_certificate_batch(db, csv_content, template_content)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    return Response(
        content=archive,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="certificates-{batch.id}.zip"',
            "X-Batch-Id": batch.id,
            "X-Recipient-Count": str(batch.recipient_count),
        },
    )