# 🎬 AI Video Assistant

An intelligent video processing application built with Streamlit that automatically transcribes, summarizes, and enables RAG-based interactive chat for YouTube videos and local audio files.

## 🚀 Features

- **Fast Caption Fetching:** Pulls existing YouTube transcripts in seconds via `youtube-transcript-api`.
- **Cloud STT Processing:** Utilizes Groq's `whisper-large-v3-turbo` API for ultra-fast audio transcription.
- **Multilingual Support:** Handles English and Hinglish audio processing using Sarvam AI integration.
- **Meeting Intelligence:** Automatically generates structured session titles, concise summaries, key decisions, action items, and open questions.
- **Interactive RAG Chat:** Ask context-aware questions directly about your uploaded meeting or video content.

## 🛠️ Tech Stack

- **Frontend:** Streamlit
- **Transcription APIs:** Groq API, Sarvam AI, `youtube-transcript-api`
- **Audio Processing:** `pydub`, `yt-dlp`
- **Language Models & RAG:** Mistral AI



