"""
app.py
------
FastAPI microservice that the Node.js backend talks to.

Endpoints:
  POST /process-video   { "youtube_url": "..." }  -> { session_id, transcript_preview }
  POST /ask              { "session_id": "...", "question": "..." } -> { answer }
  GET  /health

Run with:
  uvicorn app:app --reload --port 8000
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from transcribe import transcribe_video
from rag_engine import create_session_from_text, answer_question

load_dotenv()

if not os.getenv("MISTRAL_API_KEY"):
    print(
        "WARNING: MISTRAL_API_KEY is not set. Get a free key at "
        "https://console.mistral.ai/ and add it to your .env file."
    )

app = FastAPI(title="Video RAG Voice Assistant - Python Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in production
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProcessVideoRequest(BaseModel):
    youtube_url: str


class AskRequest(BaseModel):
    session_id: str
    question: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/process-video")
def process_video(req: ProcessVideoRequest):
    try:
        transcript = transcribe_video(req.youtube_url)
        if not transcript:
            raise HTTPException(
                status_code=422, detail="Could not extract any transcript."
            )
        session_id = create_session_from_text(transcript)
        return {
            "session_id": session_id,
            "transcript_preview": transcript[:500],
            "transcript_length": len(transcript),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/ask")
def ask(req: AskRequest):
    try:
        answer = answer_question(req.session_id, req.question)
        return {"answer": answer}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
