# Bulk Certificate Generator

A small FastAPI backend that accepts a UTF-8 CSV, creates one landscape PDF certificate per recipient, and returns the PDFs in a ZIP archive. Each batch is recorded in a local SQLite database.

## Requirements

- Python 3.10 or newer

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive documentation is at `/docs`.

## Generate certificates

Send a `multipart/form-data` request to `POST /certificates/generate` with a `csv_file` field. The CSV must be UTF-8 and include a `name` column. Optional `course` (or `achievement`) and `date` columns are printed on the certificate. An optional `template` image can be uploaded; otherwise `template.png` is used when present.

```powershell
curl.exe -X POST http://127.0.0.1:8000/certificates/generate `
  -F "csv_file=@recipients.csv" `
  -o certificates.zip
```

The response is a ZIP of PDF files. `X-Batch-Id` and `X-Recipient-Count` response headers identify the saved batch. CSV and template uploads are limited to 10 MB; batches are limited to 5,000 recipients.

## Test

```powershell
pytest
```