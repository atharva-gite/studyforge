"""Deterministic stand-in for embeddings and chat. Tests never call OpenAI."""

import hashlib
import math
import re

from app.services.language import EMBEDDING_DIMENSIONS, TransientLanguageError


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _bucket(token: str) -> int:
    digest = hashlib.sha256(token.encode()).digest()
    return int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS


class FakeLanguageModel:
    def __init__(self) -> None:
        self.complete_calls = 0
        self.embed_calls = 0
        self.transcribe_calls = 0
        self.fail_embeds = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.embed_calls += 1
        if self.fail_embeds > 0:
            self.fail_embeds -= 1
            raise TransientLanguageError("temporary outage")
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * EMBEDDING_DIMENSIONS
            tokens = _tokens(text) or ["empty"]
            for token in tokens:
                vector[_bucket(token)] += 1.0
            norm = math.sqrt(sum(value * value for value in vector)) or 1.0
            vectors.append([value / norm for value in vector])
        return vectors

    def transcribe(self, data: bytes, mime: str) -> str:
        self.transcribe_calls += 1
        return "Virtual memory maps virtual addresses to physical frames."

    def complete(self, system: str, user: str) -> dict:
        self.complete_calls += 1
        match = re.search(r"\[chunk_id=([0-9a-fA-F-]+)\]", user)
        chunk_id = match.group(1) if match else ""
        bogus = "00000000-0000-0000-0000-000000000000"
        lowered = system.lower()
        if "flashcards" in lowered:
            return {
                "cards": [
                    {
                        "front": "What does virtual memory map?",
                        "back": "Virtual addresses to physical frames.",
                        "chunk_id": chunk_id,
                    },
                    {"front": "Invented", "back": "Nope", "chunk_id": bogus},
                ]
            }
        if "multiple-choice" in lowered:
            return {
                "questions": [
                    {
                        "prompt": "What does virtual memory map?",
                        "options": ["Frames", "Disks", "Caches", "Pipes"],
                        "correct_option_index": 0,
                        "explanation": "It maps addresses to frames.",
                        "chunk_id": chunk_id,
                    },
                    {
                        "prompt": "Invented",
                        "options": ["A", "B", "C", "D"],
                        "correct_option_index": 1,
                        "explanation": "no",
                        "chunk_id": bogus,
                    },
                    {
                        "prompt": "Bad index",
                        "options": ["A", "B", "C", "D"],
                        "correct_option_index": 9,
                        "explanation": "no",
                        "chunk_id": chunk_id,
                    },
                ]
            }
        if "study focuses" in lowered:
            return {"focuses": ["Virtual memory", "Address translation"]}
        return {
            "answer": "Virtual memory maps virtual addresses to physical frames.",
            "citations": [
                {"chunk_id": chunk_id},
                {"chunk_id": bogus},
            ],
        }
