# Video RAG Voice Assistant

Ask questions — by typing or by voice — about any YouTube video (or, with
the Whisper fallback, any video/audio). The video is transcribed, indexed
with LangChain + FAISS (RAG), and queried with an LLM. The frontend speaks
answers back out loud.

## Architecture

```
 ┌───────────────┐      HTTP       ┌──────────────────┐     HTTP      ┌───────────────────────┐
 │   Frontend    │ ───────────────▶│   Node.js/Express │ ─────────────▶│  Python/FastAPI        │
 │ HTML/CSS/JS   │◀─────────────── │   (backend)       │◀───────────── │  LangChain + RAG       │
 │ Web Speech API│                 │  routes/api.js    │                │  transcribe.py         │
 └───────────────┘                 └──────────────────┘                │  rag_engine.py         │
                                                                        └───────────────────────┘
```

1. **Frontend** (`/frontend`) — plain HTML/CSS/JS.
   - Voice input: `SpeechRecognition` (Web Speech API) turns your mic
     audio into text.
   - Voice output: `SpeechSynthesisUtterance` reads the answer aloud.
   - Talks only to the Node backend (`/api/...`), never directly to Python.

2. **Node.js backend** (`/backend`) — Express server that:
   - Serves the frontend as static files.
   - Exposes `/api/process-video` and `/api/ask`, which simply proxy to
     the Python service. This keeps the browser from ever needing to know
     about the Python service or any API keys.

3. **Python service** (`/python-service`) - FastAPI + LangChain, the "brain".
   Powered by the Mistral API (mistral.ai), which has a free tier
   ("La Plateforme") for both chat and embeddings:
   - `transcribe.py` - gets the transcript. Tries YouTube's built-in
     captions first (`youtube-transcript-api`, free, no key); if that
     fails, downloads audio with `yt-dlp` and transcribes locally with
     Whisper (open-source, runs on your machine, free).
   - `rag_engine.py` - splits the transcript into chunks
     (`RecursiveCharacterTextSplitter`), embeds them with Mistral's
     `mistral-embed` model, stores them in a FAISS vector index per
     video ("session"), and answers questions with a LangChain
     `RetrievalQA` chain using Mistral's `mistral-small-latest` chat
     model (retrieve top-k relevant chunks, stuff into a prompt, LLM
     answers only from that context).
   - `app.py` - the FastAPI app wiring it all together.

   The only account you need is a free Mistral API key (no credit card
   for the free tier) at https://console.mistral.ai/ - transcription
   still runs locally at no cost either way.

## Setup

### 1. Python service (RAG / LangChain)

```bash
cd python-service
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# get a free key at https://console.mistral.ai/ and paste it into
# .env as MISTRAL_API_KEY

# ffmpeg is required by yt-dlp/whisper for the audio fallback path:
# macOS:   brew install ffmpeg
# Ubuntu:  sudo apt install ffmpeg
# Windows: https://ffmpeg.org/download.html

uvicorn app:app --reload --port 8000
```

### 2. Node.js backend

```bash
cd backend
npm install
cp .env.example .env   # defaults are fine for local dev
npm run dev             # or: npm start
```

### 3. Open the app

Visit **http://localhost:5000** — the Node server serves the frontend
directly, so there's nothing extra to run for the UI.

## Usage

1. Paste a YouTube URL and click **Process Video**. This transcribes the
   video and builds a searchable vector index (may take 10s–2min
   depending on video length and whether Whisper fallback kicks in).
2. Ask a question by typing, or click the 🎤 button and speak.
3. The answer appears in the chat and is read aloud (toggle "Speak
   answers" off to disable).

## Notes & things you may want to extend

- **LLM/embeddings provider**: currently Mistral's `mistral-small-latest`
  for chat and `mistral-embed` for embeddings, both via `langchain-mistralai`.
  Mistral's free tier has rate limits (requests per second/month); if you
  outgrow it, swap in Groq, a local model via Ollama, or any other
  LangChain-supported provider by editing `rag_engine.py`.
- **Persistence**: FAISS indexes are saved to `python-service/indexes/`,
  so sessions survive a service restart — swap in Chroma/Pinecone/Weaviate
  for production-scale or multi-user needs.
- **Non-English videos**: `youtube-transcript-api` is asked for English
  and Hindi captions by default — add more language codes in
  `transcribe.py`.
- **Security**: this scaffold is for local dev — add auth, rate limiting,
  and input validation before deploying publicly, and restrict CORS
  origins in both `app.py` and `server.js`.
