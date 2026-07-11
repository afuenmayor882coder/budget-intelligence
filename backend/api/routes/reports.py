"""Report export API routes."""
from fastapi import APIRouter
from fastapi.responses import FileResponse

from core.database import db_context
from services.narrative.export.report_export import export_markdown, export_pdf, REPORTS_DIR

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/monthly/markdown")
def export_monthly_markdown():
    with db_context() as conn:
        result = export_markdown(conn)
    return result


@router.post("/monthly/pdf")
def export_monthly_pdf():
    with db_context() as conn:
        result = export_pdf(conn)
    return result


@router.get("/download/{filename}")
def download_report(filename: str):
    path = REPORTS_DIR / filename
    if not path.exists():
        from fastapi import HTTPException
        raise HTTPException(404, "Report not found")
    return FileResponse(path, filename=filename)
