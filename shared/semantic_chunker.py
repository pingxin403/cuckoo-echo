from typing import Any
from pydantic import BaseModel
import re


class Chunk(BaseModel):
    id: str
    text: str
    start_char: int
    end_char: int
    parent_id: str | None = None
    metadata: dict[str, Any] = {}


class SemanticChunker:
    def __init__(self, embedding_service=None):
        self.embedding_service = embedding_service
        self.min_chunk_size = 200
        self.max_chunk_size = 1000
        self.overlap_size = 100

    def split_by_semantics(
        self,
        text: str,
        parent_id: str | None = None,
    ) -> list[Chunk]:
        sentences = self._split_into_sentences(text)
        
        chunks = []
        current_chunk = ""
        current_start = 0
        
        for i, sentence in enumerate(sentences):
            sentence_start = text.find(sentence, current_start)
            sentence_end = sentence_start + len(sentence)
            
            if len(current_chunk) + len(sentence) > self.max_chunk_size and current_chunk:
                chunk = Chunk(
                    id=f"chunk_{len(chunks)}",
                    text=current_chunk.strip(),
                    start_char=current_start,
                    end_char=sentence_start,
                    parent_id=parent_id,
                )
                chunks.append(chunk)
                
                overlap_start = max(0, len(current_chunk) - self.overlap_size)
                current_chunk = current_chunk[overlap_start:] + " " + sentence
                current_start = sentence_start
            else:
                if not current_chunk:
                    current_start = sentence_start
                current_chunk += " " + sentence
        
        if current_chunk.strip():
            chunks.append(Chunk(
                id=f"chunk_{len(chunks)}",
                text=current_chunk.strip(),
                start_char=current_start,
                end_char=len(text),
                parent_id=parent_id,
            ))
        
        return chunks

    def preserve_hierarchy(
        self,
        text: str,
        headings: list[tuple[str, str]],
    ) -> list[Chunk]:
        chunks = []
        
        if not headings:
            return self.split_by_semantics(text)
        
        sorted_headings = sorted(headings, key=lambda x: text.find(x[1]) if x[1] in text else 0)
        
        for i, (level, heading_text) in enumerate(sorted_headings):
            start = text.find(heading_text)
            if start == -1:
                continue
            
            if i + 1 < len(sorted_headings):
                next_heading = sorted_headings[i + 1][1]
                end = text.find(next_heading)
            else:
                end = len(text)
            
            section_text = text[start:end]
            
            section_chunks = self.split_by_semantics(section_text, parent_id=None)
            for chunk in section_chunks:
                chunk.metadata["heading"] = heading_text
                chunk.metadata["level"] = level
            chunks.extend(section_chunks)
        
        return chunks

    def add_overlap(
        self,
        chunks: list[Chunk],
    ) -> list[Chunk]:
        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        sentence_pattern = r"(?<=[.!?])\s+"
        sentences = re.split(sentence_pattern, text)
        return [s.strip() for s in sentences if s.strip()]
