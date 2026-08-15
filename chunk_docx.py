"""
Chunking script — splits markdown documents into sections at heading boundaries.

Logic (in plain terms):
1. Read the file line by line.
2. Every time we see a heading line (# Heading, or **1. Bold Title**),
   close off whatever we were collecting and start a new chunk.
3. If a chunk ends up too long, split it further at paragraph breaks.
4. Save every chunk with metadata: which file it came from, which section it is.
"""

import re
import json


def chunk_by_headings(text, source_name, max_chars=1800):
    lines = text.split('\n')

    sections = []                  # will hold (heading, content) pairs
    current_heading = "Introduction"
    current_lines = []             # lines collected under the current heading

    # Patterns that count as a "heading line"
    heading_pattern = re.compile(r'^#{1,3}\s+(.*)')          # markdown: #, ##, ###
    bold_num_pattern = re.compile(r'^\*\*\d+\.\s+.*\*\*$')   # bold numbered title: **1. Objective**

    for line in lines:
        is_heading = heading_pattern.match(line) or bold_num_pattern.match(line.strip())

        if is_heading:
            # Close off the previous chunk (if we collected anything)
            if current_lines:
                sections.append((current_heading, '\n'.join(current_lines).strip()))
            # Start a new chunk under this heading
            current_heading = line.strip().lstrip('#').strip()
            current_lines = []
        else:
            # Just content — add it to the current pile
            current_lines.append(line)

    # Don't forget the last chunk after the loop ends
    if current_lines:
        sections.append((current_heading, '\n'.join(current_lines).strip()))

    # Second pass: split any chunk that's too long, at paragraph breaks only
    chunks = []
    for heading, content in sections:
        if not content.strip():
            continue  # skip empty sections

        if len(content) <= max_chars:
            chunks.append({"source": source_name, "section": heading, "text": content})
        else:
            paragraphs = content.split('\n\n')
            buffer = ""
            part_num = 1
            for para in paragraphs:
                if len(buffer) + len(para) > max_chars and buffer:
                    chunks.append({
                        "source": source_name,
                        "section": f"{heading} (part {part_num})",
                        "text": buffer.strip()
                    })
                    part_num += 1
                    buffer = para
                else:
                    buffer += "\n\n" + para if buffer else para
            if buffer.strip():
                chunks.append({
                    "source": source_name,
                    "section": f"{heading} (part {part_num})",
                    "text": buffer.strip()
                })

    return chunks


if __name__ == "__main__":
    # Map: a friendly name -> path to the markdown file
    files = {
        "compressor_audit": "compressor_audit.md",
        "boiler_audit": "boiler_audit.md",
        "energy_saving_ppt": "energy_saving_ppt.md",
    }

    all_chunks = []
    for name, path in files.items():
        with open(path, encoding="utf-8") as f:
            text = f.read()
        all_chunks.extend(chunk_by_headings(text, name))

    with open("chunks.json", "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2)

    print(f"Total chunks created: {len(all_chunks)}")
    for c in all_chunks:
        print(f"[{c['source']}] {c['section']} — {len(c['text'])} chars")