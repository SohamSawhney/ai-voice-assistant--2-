const express = require("express");
const axios = require("axios");

const router = express.Router();

const PYTHON_SERVICE_URL =
  process.env.PYTHON_SERVICE_URL || "http://localhost:8000";

/**
 * POST /api/process-video
 * body: { youtube_url }
 * Kicks off transcription + RAG index creation in the Python service.
 */
router.post("/process-video", async (req, res) => {
  const { youtube_url } = req.body;

  if (!youtube_url) {
    return res.status(400).json({ error: "youtube_url is required" });
  }

  try {
    const response = await axios.post(
      `${PYTHON_SERVICE_URL}/process-video`,
      { youtube_url },
      { timeout: 10 * 60 * 1000 } // transcription can take a while
    );
    return res.json(response.data);
  } catch (err) {
    const detail = err.response?.data?.detail || err.message;
    return res.status(err.response?.status || 500).json({ error: detail });
  }
});

/**
 * POST /api/ask
 * body: { session_id, question }
 * Forwards a question to the RAG/LangChain QA chain.
 */
router.post("/ask", async (req, res) => {
  const { session_id, question } = req.body;

  if (!session_id || !question) {
    return res
      .status(400)
      .json({ error: "session_id and question are required" });
  }

  try {
    const response = await axios.post(`${PYTHON_SERVICE_URL}/ask`, {
      session_id,
      question,
    });
    return res.json(response.data);
  } catch (err) {
    const detail = err.response?.data?.detail || err.message;
    return res.status(err.response?.status || 500).json({ error: detail });
  }
});

/**
 * GET /api/health
 * Checks that both Node and the Python service are alive.
 */
router.get("/health", async (req, res) => {
  try {
    const response = await axios.get(`${PYTHON_SERVICE_URL}/health`, {
      timeout: 3000,
    });
    return res.json({ node: "ok", python: response.data });
  } catch (err) {
    return res
      .status(503)
      .json({ node: "ok", python: "unreachable", error: err.message });
  }
});

module.exports = router;
