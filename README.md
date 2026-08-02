<img width="898" height="888" alt="image" src="https://github.com/user-attachments/assets/f747fbd3-d6d7-4625-870c-1fa537a6d239" />



Tech stack
Layer	Technology	Role
Frontend	HTML, CSS, vanilla JS	UI, voice input/output (Web Speech API)
Backend	Node.js, Express	Serves the frontend, proxies API calls
AI service	Python, FastAPI	Transcription + RAG pipeline
Orchestration	LangChain	Text splitting, retrieval, prompt chaining
Vector store	FAISS	Stores/searches transcript embeddings
LLM + embeddings	Mistral API (free tier)	Answers questions, generates embeddings
Captions	youtube-transcript-api	Primary transcript source
Fallback transcription	yt-dlp + Groq-hosted Whisper API	For videos with no captions




facing problem in deploying on render due to whisper ai  
