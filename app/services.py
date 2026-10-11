from uuid import uuid4

from sqlalchemy.orm import Session

from app.generator import generate_archive, parse_recipients
from app.models import CertificateBatch


def create_certificate_batch(
    db: Session, csv_content: bytes, template: bytes | None
) -> tuple[CertificateBatch, bytes]:
    recipients = parse_recipients(csv_content)
    batch = CertificateBatch(id=str(uuid4()), recipient_count=len(recipients))
    archive = generate_archive(recipients, template)
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch, archive