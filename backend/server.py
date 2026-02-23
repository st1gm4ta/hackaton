import json
import os
import re
from pathlib import Path
from typing import Iterator

import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
MEMORY_STORE_PATH = BASE_DIR / "memory_store.json"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

HIGH_RISK_KEYWORDS = {
    "zelfmoord",
    "suicide",
    "verkrachting",
    "rape",
    "ik wil dood",
    "mezelf pijn",
    "acute nood",
}

SENSITIVE_KEYWORDS = {
    "depressie",
    "angst",
    "paniek",
    "ptss",
    "therapie",
    "medisch",
    "dokter",
    "juridisch",
    "advocaat",
    "misdaad",
    "crime",
}


class HistoryItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    user_text: str
    history: list[HistoryItem] = Field(default_factory=list)
    conversation_id: str | None = None


def tokenize(text: str) -> list[str]:
    return [t for t in re.split(r"\W+", text.lower()) if t]


def detect_mode(user_text: str) -> str:
    text = user_text.lower()
    if any(keyword in text for keyword in HIGH_RISK_KEYWORDS):
        return "high_risk"
    if any(keyword in text for keyword in SENSITIVE_KEYWORDS):
        return "serious"
    return "playful"


def retrieve_facts(query: str) -> list[str]:
    try:
        if not MEMORY_STORE_PATH.exists():
            return []
        with MEMORY_STORE_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)

        items: list[str] = []
        if isinstance(data, list):
            for row in data:
                if isinstance(row, str):
                    items.append(row)
                elif isinstance(row, dict):
                    text = row.get("text") or row.get("content") or ""
                    if isinstance(text, str) and text.strip():
                        items.append(text.strip())

        query_tokens = set(tokenize(query))
        scored: list[tuple[int, str]] = []
        for item in items:
            overlap = len(query_tokens.intersection(set(tokenize(item))))
            if overlap > 0:
                scored.append((overlap, item))

        scored.sort(key=lambda value: value[0], reverse=True)
        return [item for _, item in scored[:8]]
    except Exception:
        return []


def build_system_prompt(mode: str, facts: list[str]) -> str:
    base_rules = [
        "Antwoord ALTIJD in het Nederlands.",
        "Houd het kort: 1-4 zinnen, max 80 woorden.",
        "Gebruik simpele taal alsof je tegen een 14-jarige praat.",
        "Geef kleine feiten en praktische tips.",
    ]

    if mode == "playful":
        tone = "Onderwerp is niet serieus: lieve tamagotchi/diertje-stijl is oké, klein beetje speels."
    elif mode == "high_risk":
        tone = "Onderwerp is HIGH_RISK: blijf rustig, serieus, veilig advies, geen emoji of diergeluid."
    else:
        tone = "Onderwerp is serieus: neutraal, rustig en feitelijk, zonder speelsheid."

    facts_block = "\n".join(f"- {fact}" for fact in facts) if facts else "- (geen facts gevonden)"

    return (
        "\n".join(base_rules)
        + "\n"
        + tone
        + "\nRetrieved facts:\n"
        + facts_block
        + "\nGebruik deze facts als ze passen; verzin geen details die er niet staan."
        + "\nAls facts leeg zijn: zeg eerlijk dat je het niet zeker weet en stel 1 korte vervolgvraag of geef 1 simpele zoek-tip."
    )


def shortify_answer(answer: str) -> str:
    cleaned = re.sub(r"\s+", " ", answer).strip()
    words = cleaned.split()
    if len(words) > 80:
        cleaned = " ".join(words[:80]).rstrip(".,;:!?") + "."

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]
    if len(sentences) > 4:
        cleaned = " ".join(sentences[:4]).strip()
        if cleaned and cleaned[-1] not in ".!?":
            cleaned += "."

    if not cleaned:
        return "Sorry, ik weet het nu even niet zeker."
    return cleaned


def call_ollama(messages: list[dict], stream: bool = False):
    payload = {"model": MODEL_NAME, "messages": messages, "stream": stream}
    return requests.post(
        f"{OLLAMA_URL}/api/chat",
        json=payload,
        timeout=120,
        stream=stream,
    )


app = FastAPI(title="Robot Buddy Local Backend")


@app.get("/health")
def health():
    return {"ok": True, "model": MODEL_NAME}


@app.post("/chat")
def chat(request: ChatRequest):
    mode = detect_mode(request.user_text)
    facts = retrieve_facts(request.user_text)

    system_prompt = build_system_prompt(mode, facts)
    messages = [{"role": "system", "content": system_prompt}]
    for item in request.history[-12:]:
        role = "assistant" if item.role == "assistant" else "user"
        messages.append({"role": role, "content": item.content})
    messages.append({"role": "user", "content": request.user_text})

    try:
        response = call_ollama(messages, stream=False)
        response.raise_for_status()
        data = response.json()
        raw_answer = data.get("message", {}).get("content", "")
        answer = shortify_answer(raw_answer)
        return {"mode": mode, "answer": answer, "facts_used": facts[:5]}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "mode": mode,
                "answer": "Ik kan het model nu niet bereiken. Start Ollama en probeer opnieuw.",
                "facts_used": facts[:5],
            },
        )


@app.get("/chat/stream")
def chat_stream(user_text: str):
    mode = detect_mode(user_text)
    facts = retrieve_facts(user_text)
    system_prompt = build_system_prompt(mode, facts)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]

    def event_generator() -> Iterator[str]:
        try:
            response = call_ollama(messages, stream=True)
            response.raise_for_status()
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                data = json.loads(line)
                content = data.get("message", {}).get("content", "")
                if content:
                    yield f"data: {json.dumps({'chunk': content})}\n\n"
                if data.get("done"):
                    break
            yield f"data: {json.dumps({'done': True, 'mode': mode, 'facts_used': facts[:5]})}\n\n"
        except Exception:
            error = {
                "error": "Ik kan het model nu niet bereiken. Start Ollama en probeer opnieuw.",
                "mode": mode,
            }
            yield f"data: {json.dumps(error)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
