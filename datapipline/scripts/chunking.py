import re
from langchain_text_splitters.markdown import MarkdownHeaderTextSplitter
from langchain_core.documents import Document

test_file = "test_text_book.pdf"

def chunk_chapter(chapter_num: int, chapter_text: str, source_file:str) -> list[Document]:
  chapter_title = title = chapter_text.splitlines()[0]

  splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[
      ("##", "section"),
      ("###", "subsection"),
    ],
    strip_headers=False,
  )
  chunks = splitter.split_text(chapter_text)

  # 2. Enrich metadata per chunk
  enriched = []
  for idx, chunk in enumerate(chunks):
    meta = chunk.metadata
    section = meta.get("section", "")
    subsection = meta.get("subsection", "")

    # Determine content_type from section heading
    content_type = classify_content_type(section, chunk.page_content)

    # Extract concepts from heading + content
    concepts = extract_concepts(section, subsection, chunk.page_content)

    # Detect formulas, figures
    has_formulas = "$$" in chunk.page_content or "$" in chunk.page_content
    has_figures = "<!-- image -->" in chunk.page_content

    # Token count (rough)
    token_count = len(chunk.page_content) // 4

    # Build heading_path
    heading_path = f"Chapter {chapter_num}"
    if section:
      heading_path += f" > {section}"
    if subsection:
      heading_path += f" > {subsection}"

    enriched.append(Document(
      page_content=chunk.page_content,
      metadata={
        "source_file": source_file,
        "source_type": "textbook",
        "chapter_num": chapter_num,
        "chapter_title": chapter_title,
        "section": section,
        "subsection": subsection,
        "chunk_index": idx,
        "chunk_id": f"ch{chapter_num}_{idx}",
        "token_count": token_count,
        "heading_path": heading_path,
        "content_type": content_type,
        "concepts": concepts,
        "has_formulas": has_formulas,
        "has_figures": has_figures,
        # placeholder for future enrichment
        "difficulty": None,
        "question_type": None,
        "learning_objectives": [],
        "bloom_level": None,
        "prerequisite_concepts": [],
        "related_chunks": [],
      }
    ))
  return enriched


def classify_content_type(section: str, content: str) -> str:
    """Map section heading to content_type."""
    s = section.lower()
    if "learning outcome" in s:
        return "learning_outcome"
    if "box" in s or "worked example" in s:
        return "worked_example"
    if "question" in s:
        return "exercise"
    if "summary" in s:
        return "summary"
    if "definition" in s or "key term" in s:
        return "definition"
    return "theory"


def extract_concepts(section: str, subsection: str, content: str) -> list[str]:
    """Extract concept keywords from headings (simple version)."""
    concepts = []
    for text in [section, subsection]:
        if text:
            # Split on common delimiters, keep meaningful words
            words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
            concepts.extend(words)
    # Deduplicate, keep top ~5
    seen = set()
    uniq = []
    for c in concepts:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq[:5]