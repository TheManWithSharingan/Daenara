# DaenaraCV

DaenaraCV is a full-stack prototype that turns a short "professional
profile" into a guided interview, validates user answers, and generates
a **single, self-contained HTML CV** optimized for **print/PDF export**.

-   **Frontend:** React + TypeScript + React Router + Bootstrap\
-   **Backend:** FastAPI + Nebius OpenAI-compatible client\
-   **LLM models:** Qwen (chat for Q&A + coder for HTML CV generation)

> Output is HTML (not DOCX/PDF): the app generates a print-ready HTML
> document you can save as PDF from the browser.

------------------------------------------------------------------------

## What this app does

DaenaraCV implements a simple pipeline:

1.  User enters a professional profile/role (e.g., "Machine Learning
    Engineer").
2.  Backend generates a set of questions tailored to that role.
3.  User answers questions one by one.
4.  Backend validates the answer (or accepts "I don't want to answer" as
    valid).
5.  When the interview ends, backend generates a complete CV in HTML
    with embedded CSS.
6.  Frontend allows the user to download the CV as `daenara_cv.html`.

------------------------------------------------------------------------

## Architecture

### High-level flow

React UI (Browser)\
→ POST `/create_questions`\
→ FastAPI Backend\
→ LLM (Qwen chat model)\
→ Questions JSON

React UI (Q&A loop)\
→ POST `/answer_question`\
→ FastAPI Backend\
→ LLM validation\
→ Updated structured JSON

React UI\
→ POST `/create_cv`\
→ FastAPI Backend\
→ LLM (Qwen coder model)\
→ HTML CV

------------------------------------------------------------------------

## Backend (FastAPI)

Implemented in `daenaraBackend.py`.

### Endpoints

#### POST `/create_questions`

Input: `profile` (string)\
Output: JSON object containing numbered questions.

If invalid:

``` json
{ "error": "INVALID_PROFILE" }
```

------------------------------------------------------------------------

#### POST `/answer_question`

Input: - `current_info` (stringified JSON) - `question` (string) -
`answer` (string)

Output: Updated JSON with accepted Q&A pair.

If invalid:

``` json
{ "error": "INVALID ANSWER" }
```

------------------------------------------------------------------------

#### POST `/create_cv`

Input: `user_info` (stringified JSON)\
Output: Single HTML document (with embedded CSS).

Constraints enforced via prompt: - One HTML file - Embedded CSS -
Bootstrap Icons only - A4 print-ready - No invented data - No hyperlinks

------------------------------------------------------------------------

## Frontend (React + TypeScript)

Main concepts:

-   React Router for navigation (`/`, `/pipeline`, `/contacts`)
-   Stage-driven state machine (`PROFILE`, `QUESTIONS`, `GENERATING`,
    `DONE`)
-   API client wrapper with timeout and structured error handling
-   Blob-based download of generated HTML

Accessibility improvements: - Focus management on error messages - ARIA
attributes - "Skip to content" link

------------------------------------------------------------------------

## Styling

-   Bootstrap CSS + JS
-   Custom theme (`theme.css`)
-   Glassmorphism cards
-   Sticky translucent header
-   Dark gradient background
-   Custom Daenara buttons and accent styles

------------------------------------------------------------------------

## Running locally

### Backend

``` bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install fastapi uvicorn openai
```

Set environment variable:

``` bash
export NEBIUS_API_KEY="YOUR_KEY"
```

Run:

``` bash
uvicorn daenaraBackend:app --reload --host 0.0.0.0 --port 8000
```

------------------------------------------------------------------------

### Frontend

``` bash
npm install
npm run dev
```

Frontend runs on:

http://localhost:5173

Backend CORS is configured to allow this origin.

------------------------------------------------------------------------

## Known Limitations

-   Uses query parameters instead of JSON body payloads
-   No database or persistence layer
-   HTML export only (browser PDF save)
-   Contacts page is placeholder
-   No production-level auth or rate limiting

------------------------------------------------------------------------

## Roadmap Ideas

-   Add CV template upload
-   Add iterative "further questions" loop
-   Convert endpoints to JSON body with Pydantic models
-   Add server-side PDF export
-   Add multi-theme CV selection
-   Add persistence layer

------------------------------------------------------------------------

## License

This is currently a prototype/demo project.
