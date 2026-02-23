# Local Robot Buddy Chat (FastAPI + Ollama)

Dit project laat de bestaande front-end (`robot-buddy-chat-53e`) chatten met een lokaal model via Ollama.
De FastAPI backend serveert de UI op `/` en heeft chat endpoints op `/chat` en `/chat/stream`.

## Starten (2 terminals)

1. Start Ollama model:

```bash
ollama run llama3.2:1b
```

2. Start backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
```

Open daarna: http://localhost:8000

## API

### `POST /chat`
Request:

```json
{
  "user_text": "wat eet een axolotl?",
  "history": [{"role": "user", "content": "hoi"}],
  "conversation_id": "optioneel"
}
```

Response:

```json
{
  "mode": "playful",
  "answer": "...",
  "facts_used": ["..."]
}
```

### `GET /chat/stream?user_text=...`
Geeft Server-Sent Events terug met `chunk` updates.

## Memory retrieval

`backend/memory_store.json` bevat korte facts.
De backend zoekt op keyword overlap en kiest top snippets.
