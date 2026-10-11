import csv
import io
import re
import zipfile
from collections.abc import Iterable

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


MAX_RECIPIENTS = 5000
REQUIRED_COLUMNS = {"name"}


def parse_recipients(csv_content: bytes) -> list[dict[str, str]]:
    try:
        text = csv_content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        headers = {header.strip().lower() for header in (reader.fieldnames or []) if header}
        missing = REQUIRED_COLUMNS - headers
        if missing:
            raise ValueError("CSV must include a 'name' column.")

        rows = []
        for row in reader:
            normalized = {
                (key or "").strip().lower(): (value or "").strip()
                for key, value in row.items()
            }
            if not any(normalized.values()):
                continue
            if not normalized.get("name"):
                raise ValueError("Every recipient row must have a name.")
            rows.append(normalized)
            if len(rows) > MAX_RECIPIENTS:
                raise ValueError(f"A batch cannot exceed {MAX_RECIPIENTS} recipients.")
    except UnicodeDecodeError as error:
        raise ValueError("CSV must be encoded as UTF-8.") from error

    if not rows:
        raise ValueError("CSV must contain at least one recipient.")
    return rows


def _certificate_pdf(
    recipient: dict[str, str], template: bytes | None
) -> bytes:
    page_width, page_height = landscape(A4)
    output = io.BytesIO()
    pdf = canvas.Canvas(output, pagesize=(page_width, page_height))

    if template:
        pdf.drawImage(
            ImageReader(io.BytesIO(template)),
            0,
            0,
            width=page_width,
            height=page_height,
            preserveAspectRatio=False,
        )
    else:
        pdf.setStrokeColorRGB(0.12, 0.32, 0.35)
        pdf.setLineWidth(3)
        pdf.rect(24, 24, page_width - 48, page_height - 48)

    pdf.setFillColorRGB(0.10, 0.20, 0.22)
    pdf.setFont("Helvetica-Bold", 34)
    pdf.drawCentredString(page_width / 2, page_height * 0.56, recipient["name"][:100])

    course = recipient.get("course") or recipient.get("achievement")
    if course:
        pdf.setFont("Helvetica", 16)
        pdf.drawCentredString(page_width / 2, page_height * 0.45, course[:160])

    date = recipient.get("date")
    if date:
        pdf.setFont("Helvetica", 12)
        pdf.drawCentredString(page_width / 2, page_height * 0.34, date[:80])

    pdf.showPage()
    pdf.save()
    return output.getvalue()


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
    return cleaned[:60] or "recipient"


def generate_archive(
    recipients: Iterable[dict[str, str]], template: bytes | None = None
) -> bytes:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for index, recipient in enumerate(recipients, start=1):
            filename = f"{index:04d}_{_safe_filename(recipient['name'])}.pdf"
            bundle.writestr(filename, _certificate_pdf(recipient, template))
    return archive.getvalue()