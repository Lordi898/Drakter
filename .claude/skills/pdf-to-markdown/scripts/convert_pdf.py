#!/usr/bin/env python3
"""
Convert PDF files to LLM-friendly Markdown format using pymupdf4llm.
Handles complex layouts, tables, and multi-column documents.
"""
import sys
import os
from pathlib import Path

def convert_pdf_to_markdown(pdf_path, output_path=None, page_chunks=False):
    """
    Convert a PDF file to Markdown format.
    
    Args:
        pdf_path: Path to the input PDF file
        output_path: Path for the output .md file (optional, defaults to same name as PDF)
        page_chunks: If True, return list of markdown strings (one per page)
    
    Returns:
        str or list: Markdown text (or list of page texts if page_chunks=True)
    """
    try:
        import pymupdf4llm
    except ImportError:
        print("Error: pymupdf4llm is not installed.", file=sys.stderr)
        print("Install it with: pip install pymupdf4llm --break-system-packages", file=sys.stderr)
        sys.exit(1)
    
    # Convert the PDF
    if page_chunks:
        md_text = pymupdf4llm.to_markdown(pdf_path, page_chunks=True)
    else:
        md_text = pymupdf4llm.to_markdown(pdf_path)
    
    # Save to file if output path specified
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        if page_chunks:
            # If page chunks, save with page markers
            with open(output_file, 'w', encoding='utf-8') as f:
                for i, page_text in enumerate(md_text, 1):
                    f.write(f"# Page {i}\n\n")
                    f.write(page_text)
                    f.write("\n\n---\n\n")
        else:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(md_text)
        
        print(f"Converted PDF to Markdown: {output_file}")
        return str(output_file)
    
    return md_text


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_pdf.py <input.pdf> [output.md] [--page-chunks]")
        print("\nOptions:")
        print("  --page-chunks    Split output into separate page sections")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    output_md = None
    page_chunks = False
    
    # Parse arguments
    if len(sys.argv) > 2:
        for arg in sys.argv[2:]:
            if arg == "--page-chunks":
                page_chunks = True
            elif not arg.startswith("--"):
                output_md = arg
    
    # If no output specified, use same name as input with .md extension
    if output_md is None:
        output_md = str(Path(input_pdf).with_suffix('.md'))
    
    # Convert the PDF
    result = convert_pdf_to_markdown(input_pdf, output_md, page_chunks)
    
    if isinstance(result, str):
        print(f"Markdown saved to: {result}")
