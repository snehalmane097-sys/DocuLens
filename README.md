# DocuLens AI

**Intelligent invoice extraction, validation, and reconciliation.**

DocuLens AI converts invoice PDFs and images into structured financial records, validates invoice totals, and helps users identify discrepancies before approval.

## Features

- **Invoice Extraction:** Extracts supplier details, invoice numbers, dates, amounts, and tax fields from supported documents.
- **OCR Support:** Uses local Tesseract OCR to process scanned PDFs and PNG/JPEG images.
- **Financial Validation:** Checks subtotal, GST components, and total calculations where sufficient data is available.
- **Evidence & Review:** Retains extraction evidence and flags uncertain fields for human verification.
- **Document History:** Stores analyzed records and versioned reviews using SQLite.
- **Reconciliation:** Generates reports to help identify financial discrepancies.
- **Analytics Dashboard:** Displays invoice activity and available financial summaries.
- **Responsive UI:** Built with a clean, modern dashboard for desktop and mobile.

## Tech Stack

- **Frontend:** Next.js, React, TypeScript, Tailwind CSS
- **Backend:** Python, FastAPI
- **Database:** SQLite
- **Document Processing:** pypdf, Poppler, Tesseract OCR

## Getting Started

### Prerequisites

- Node.js and npm
- Python and the project's backend dependencies
- Tesseract OCR with English language data for image and scanned-PDF processing

### 1. Start the Backend

Open PowerShell:

```powershell
cd C:\Doculens
$env:DOCULENS_TESSERACT_PATH = "C:\Program Files\Tesseract-OCR\tesseract.exe"
.\backend\run.ps1
```

Keep the terminal open.

### 2. Start the Frontend

Open a second terminal:

```powershell
cd C:\Doculens\frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### 3. API Documentation

With the backend running, visit [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## How It Works

1. Upload an invoice PDF or supported image.
2. Extract text directly from digital PDFs or use local OCR for scanned documents and images.
3. Parse invoice fields and validate supported financial calculations.
4. Review extracted values, evidence, and flagged uncertainties.
5. Save reviews and generate reconciliation reports.

## Testing

Run the backend tests:

```powershell
cd C:\Doculens\backend
.\.venv\Scripts\python.exe -m pytest -q
```

Run the frontend checks:

```powershell
cd C:\Doculens\frontend
npm test
npm run typecheck
npm run lint
npm run build
```

## Limitations

- Extraction accuracy depends on document quality and layout.
- Handwritten invoice recognition has not been fully verified.
- Ambiguous fields remain unknown and may require human review.
- Successful arithmetic validation does not establish that an invoice is genuine.

## Privacy

OCR is designed to run locally through Tesseract. Avoid committing invoice data, local databases, environment files, or credentials to version control.