require("dotenv").config();
const path = require("path");
const express = require("express");
const cors = require("cors");

const apiRoutes = require("./routes/api");

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json({ limit: "5mb" }));

// Serve the frontend (HTML/CSS/JS) as static files
app.use(express.static(path.join(__dirname, "..", "frontend")));

// API routes -> forwarded to the Python RAG/LangChain service
app.use("/api", apiRoutes);

// Fallback: send index.html for any non-API route (simple SPA-style serving)
app.get("*", (req, res) => {
  res.sendFile(path.join(__dirname, "..", "frontend", "index.html"));
});

app.listen(PORT, () => {
  console.log(`Node backend running on http://localhost:${PORT}`);
});
