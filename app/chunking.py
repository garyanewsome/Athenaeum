import re

MAX_CHUNK_CHARS = 1500


def chunk_markdown(text: str) -> list[str]:
    """Split on markdown headers first (keeps notes' own structure), then
    further split any section that's still too long by paragraph."""
    sections = re.split(r"\n(?=#{1,6} )", text.strip())

    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        if len(section) <= MAX_CHUNK_CHARS:
            chunks.append(section)
            continue

        paragraphs = section.split("\n\n")
        current = ""
        for paragraph in paragraphs:
            if len(current) + len(paragraph) + 2 <= MAX_CHUNK_CHARS:
                current = f"{current}\n\n{paragraph}" if current else paragraph
            else:
                if current:
                    chunks.append(current)
                current = paragraph
        if current:
            chunks.append(current)

    return chunks
