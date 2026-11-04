---
name: pdf-to-markdown
description: Convert PDF documents to LLM-friendly Markdown format using pymupdf4llm. Use when working with PDF files that need to be converted to markdown, extracted as text for analysis, or made accessible for LLM processing. Handles complex layouts, tables, multi-column documents, and preserves formatting structure.
---

# PDF to Markdown Converter

Convert PDF documents to clean, LLM-friendly Markdown format using the pymupdf4llm library.

## Quick Start

### Install Dependencies

```bash
pip install pymupdf4llm --break-system-packages
```

### Basic Conversion

Convert a PDF to Markdown:

```python
from scripts.convert_pdf import convert_pdf_to_markdown

# Convert and save
convert_pdf_to_markdown("document.pdf", "output.md")

# Convert and return as string
md_text = convert_pdf_to_markdown("document.pdf")
```

### Using the Script Directly

```bash
python scripts/convert_pdf.py input.pdf output.md
```

## Common Use Cases

### 1. Convert Uploaded PDF

When a user uploads a PDF and asks to convert it or extract its text:

```python
from scripts.convert_pdf import convert_pdf_to_markdown

# Get the PDF from uploads
pdf_path = "/mnt/user-data/uploads/document.pdf"

# Convert to markdown
md_path = "/mnt/user-data/outputs/document.md"
convert_pdf_to_markdown(pdf_path, md_path)
```

### 2. Page-by-Page Conversion

For large documents where page boundaries matter:

```python
# Convert with page chunks
convert_pdf_to_markdown("large_doc.pdf", "output.md", page_chunks=True)
```

This creates a markdown file with clear page separators.

### 3. In-Memory Processing

When you need the text for immediate processing without saving:

```python
# Get markdown as string
md_text = convert_pdf_to_markdown("document.pdf")

# Now process the text
print(md_text[:500])  # Show first 500 chars
```

## Features

- **Complex layouts**: Handles multi-column documents, headers, footers
- **Tables**: Converts tables to markdown table format
- **Structure preservation**: Maintains headings, lists, formatting
- **LLM-optimized**: Output designed for language model consumption
- **Page chunking**: Optional page-by-page splitting

## Workflow

1. Check if pymupdf4llm is installed (script handles this)
2. Call `convert_pdf_to_markdown()` with the PDF path
3. Optionally specify output path and page chunking
4. Script returns the markdown text or path to saved file

## Script Reference

The `scripts/convert_pdf.py` script can be:
- Imported as a module and called from Python
- Run directly from command line
- Used in both claude.ai and local Claude Code environments

For detailed library features and options, see `references/pymupdf4llm.md`.
