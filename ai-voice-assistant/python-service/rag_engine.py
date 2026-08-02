"""
rag_engine.py
-------------
All the LangChain / RAG logic lives here — powered by the Mistral API
(mistral.ai), which offers a free tier ("La Plateforme") for both chat
and embedding models. Get a free key at https://console.mistral.ai/

Steps:
  1. Split transcript into chunks
  2. Embed chunks + store them in a FAISS vector index (one per "session")
  3. Given a question, retrieve relevant chunks and ask the LLM to answer
     using ONLY that context (classic Retrieval-Augmented Generation)

Each processed video gets a `session_id`. The FAISS index for that session
is kept in memory (and persisted to disk under ./indexes/) so follow-up
questions don't require re-embedding the transcript.
"""

import os
import uuid
from typing import Dict

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_mistralai import MistralAIEmbeddings, ChatMistralAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

INDEX_DIR = os.path.join(os.path.dirname(__file__), "indexes")
os.makedirs(INDEX_DIR, exist_ok=True)

# Loaded once and reused across sessions.
_embeddings = None


def _get_embeddings() -> MistralAIEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = MistralAIEmbeddings(model="mistral-embed")
    return _embeddings


# In-memory cache: session_id -> FAISS vectorstore
_VECTORSTORE_CACHE: Dict[str, FAISS] = {}

PROMPT_TEMPLATE = """You are a helpful assistant answering questions about a
video transcript. Use ONLY the context below to answer. If the answer isn't
in the context, say you don't know based on the video.

Context:
{context}

Question: {question}

Answer concisely and clearly, in a way that sounds natural if read aloud:"""

QA_PROMPT = PromptTemplate(
    template=PROMPT_TEMPLATE, input_variables=["context", "question"]
)


def create_session_from_text(transcript: str) -> str:
    """Chunk + embed a transcript, store it as a new FAISS session."""
    session_id = str(uuid.uuid4())

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=150
    )
    chunks = splitter.split_text(transcript)

    vectorstore = FAISS.from_texts(chunks, _get_embeddings())

    vectorstore.save_local(os.path.join(INDEX_DIR, session_id))
    _VECTORSTORE_CACHE[session_id] = vectorstore

    return session_id


def _load_vectorstore(session_id: str) -> FAISS:
    if session_id in _VECTORSTORE_CACHE:
        return _VECTORSTORE_CACHE[session_id]

    path = os.path.join(INDEX_DIR, session_id)
    if not os.path.isdir(path):
        raise ValueError(f"Unknown session_id: {session_id}")

    vectorstore = FAISS.load_local(
        path, _get_embeddings(), allow_dangerous_deserialization=True
    )
    _VECTORSTORE_CACHE[session_id] = vectorstore
    return vectorstore


def answer_question(session_id: str, question: str) -> str:
    """Run a RetrievalQA chain against the stored transcript for a session."""
    vectorstore = _load_vectorstore(session_id)

    # Mistral's free-tier chat model.
    llm = ChatMistralAI(model="mistral-small-latest", temperature=0.2)

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=vectorstore.as_retriever(search_kwargs={"k": 4}),
        chain_type="stuff",
        chain_type_kwargs={"prompt": QA_PROMPT},
    )

    result = qa_chain.invoke({"query": question})
    return result["result"]
