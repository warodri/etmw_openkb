#!/usr/bin/env python3
"""Convert one uploaded file to Markdown text on stdout.
Plain text, Markdown and HTML-as-text pass straight through; PDF, Word, EPUB and images
go through Docling (run this with the intake venv python: data/intake/venv/bin/python)."""
import os, sys
path = sys.argv[1]
ext = os.path.splitext(path)[1].lower()
if ext in (".txt", ".md", ".markdown", ".text"):
    sys.stdout.write(open(path, encoding="utf-8", errors="replace").read())
else:
    from docling.document_converter import DocumentConverter
    sys.stdout.write(DocumentConverter().convert(path).document.export_to_markdown())
