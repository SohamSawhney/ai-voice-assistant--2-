const API_BASE = "/api";

const videoUrlInput = document.getElementById("videoUrl");
const processBtn = document.getElementById("processBtn");
const videoStatus = document.getElementById("videoStatus");
const chatSection = document.getElementById("chatSection");
const chatWindow = document.getElementById("chatWindow");
const questionInput = document.getElementById("questionInput");
const sendBtn = document.getElementById("sendBtn");
const micBtn = document.getElementById("micBtn");
const voiceOutputToggle = document.getElementById("voiceOutputToggle");

let sessionId = null;

/* ---------------------------------------------------------------------- */
/* Chat UI helpers                                                        */
/* ---------------------------------------------------------------------- */

function addMessage(text, role) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function setStatus(message, type = "") {
  videoStatus.textContent = message;
  videoStatus.className = `status ${type}`;
}

/* ---------------------------------------------------------------------- */
/* Step 1: Process the video (transcribe + build RAG index)               */
/* ---------------------------------------------------------------------- */

processBtn.addEventListener("click", async () => {
  const url = videoUrlInput.value.trim();
  if (!url) {
    setStatus("Please paste a YouTube URL first.", "error");
    return;
  }

  processBtn.disabled = true;
  setStatus("Transcribing video and building knowledge base... this can take a minute.");

  try {
    const res = await fetch(`${API_BASE}/process-video`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ youtube_url: url }),
    });
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || "Failed to process video");
    }

    sessionId = data.session_id;
    setStatus(
      `Ready! Transcript length: ${data.transcript_length} characters.`,
      "success"
    );
    chatSection.classList.remove("hidden");
    chatWindow.innerHTML = "";
    addMessage("Video processed. Ask me anything about it!", "system");
  } catch (err) {
    setStatus(err.message, "error");
  } finally {
    processBtn.disabled = false;
  }
});

/* ---------------------------------------------------------------------- */
/* Step 2: Ask questions (RAG query)                                      */
/* ---------------------------------------------------------------------- */

async function askQuestion(question) {
  if (!sessionId) {
    addMessage("Please process a video first.", "system");
    return;
  }

  addMessage(question, "user");
  questionInput.value = "";

  const thinkingMsg = document.createElement("div");
  thinkingMsg.className = "msg bot";
  thinkingMsg.textContent = "Thinking...";
  chatWindow.appendChild(thinkingMsg);
  chatWindow.scrollTop = chatWindow.scrollHeight;

  try {
    const res = await fetch(`${API_BASE}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, question }),
    });
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || "Failed to get an answer");
    }

    thinkingMsg.textContent = data.answer;

    if (voiceOutputToggle.checked) {
      speak(data.answer);
    }
  } catch (err) {
    thinkingMsg.textContent = `Error: ${err.message}`;
  }
}

sendBtn.addEventListener("click", () => {
  const question = questionInput.value.trim();
  if (question) askQuestion(question);
});

questionInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    const question = questionInput.value.trim();
    if (question) askQuestion(question);
  }
});

/* ---------------------------------------------------------------------- */
/* Voice input (speech-to-text) using the Web Speech API                  */
/* ---------------------------------------------------------------------- */

const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let listening = false;

if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.lang = "en-US";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    questionInput.value = transcript;
    askQuestion(transcript);
  };

  recognition.onend = () => {
    listening = false;
    micBtn.classList.remove("listening");
  };

  recognition.onerror = () => {
    listening = false;
    micBtn.classList.remove("listening");
  };
} else {
  micBtn.disabled = true;
  micBtn.title = "Voice input not supported in this browser";
}

micBtn.addEventListener("click", () => {
  if (!recognition) return;

  if (listening) {
    recognition.stop();
    return;
  }

  listening = true;
  micBtn.classList.add("listening");
  recognition.start();
});

/* ---------------------------------------------------------------------- */
/* Voice output (text-to-speech) using SpeechSynthesis                    */
/* ---------------------------------------------------------------------- */

function speak(text) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel(); // stop any ongoing speech
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1;
  utterance.pitch = 1;
  window.speechSynthesis.speak(utterance);
}
