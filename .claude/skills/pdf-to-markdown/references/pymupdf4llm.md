# pymupdf4llm Reference

## Core Features

- **Handles complex layouts**: Multi-column documents, tables, headers/footers
- **Preserves structure**: Maintains headings, lists, formatting
- **Table extraction**: Converts tables to markdown format
- **Image handling**: Can extract and reference images
- **Page chunking**: Option to split by pages for better control

## Common Options

### Basic Conversion
```python
import pymupdf4llm
md_text = pymupdf4llm.to_markdown("document.pdf")
```

### Page Chunks
Split document into per-page markdown sections:
```python
md_text = pymupdf4llm.to_markdown("document.pdf", page_chunks=True)
# Returns list of strings, one per page
```

### Advanced Options
- `pages`: List of specific page numbers to convert (e.g., `[0, 1, 2]`)
- `dpi`: Image resolution for embedded images (default 150)
- `page_chunks`: Boolean to split by pages

## Output Format

The library produces clean markdown that:
- Uses proper heading hierarchy (#, ##, ###)
- Converts tables to markdown table syntax
- Maintains paragraph structure
- Preserves lists (ordered and unordered)
- Handles code blocks and preformatted text

## Installation

```bash
pip install pymupdf4llm --break-system-packages
```

## Use Cases

1. **Documentation conversion**: Technical manuals, guides, specifications
2. **LLM preprocessing**: Making PDFs accessible to language models
3. **Content extraction**: Pulling structured text from complex PDFs
4. **Archival**: Converting PDFs to more flexible markdown format
