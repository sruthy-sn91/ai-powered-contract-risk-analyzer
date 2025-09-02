import os
import re
import io
import shutil
from dataclasses import dataclass
from tempfile import NamedTemporaryFile
from typing import List, Optional, Dict, Any

import fitz  # PyMuPDF
import pdfplumber
from fastapi import UploadFile, HTTPException

try:
    from docx import Document  # python-docx
except Exception:  # pragma: no cover
    Document = None

try:
    import pytesseract
    from PIL import Image
except Exception:  # pragma: no cover
    pytesseract = None
    Image = None

# ---------- Simple schema-compatible containers ----------

@dataclass
class PageOut:
    page_number: int
    text: str
    ocr_used: bool
    rotation: int
    has_tables: bool
    watermarks: List[str]
    quality_score: float

@dataclass
class ClauseOut:
    id: str
    title: str
    heading: str
    start: int
    end: int

@dataclass
class ParsingResultOut:
    pages: List[PageOut]
    normalized_text: str
    clauses: List[ClauseOut]
    meta: Dict[str, Any]


# ---------- Heuristics & helpers ----------

GOV_LAW_RE = re.compile(r"(?i)govern(ed|ing)\s+by\s+the\s+laws?\s+of\s+([A-Za-z ]+)")
CURRENCY_RE = re.compile(r"(?i)\b(USD|EUR|GBP|JPY|INR|AUD|CAD|CHF|SGD|CNY|RMB|HKD|AED|SAR)\b")
LANG_HINTS = {
    "en": [r"\bthe\b", r"\band\b", r"\bagreement\b"],
    "fr": [r"\ble\b", r"\bet\b", r"\bcontrat\b"],
    "de": [r"\bdas\b", r"\bund\b", r"\bvertrag\b"],
    "es": [r"\bel\b", r"\by\b", r"\bacuerdo\b"],
}

def detect_languages(text: str) -> List[str]:
    hits = []
    lower = text.lower()
    for lang, pats in LANG_HINTS.items():
        score = sum(1 for p in pats if re.search(p, lower))
        if score >= 2:
            hits.append(lang)
    return hits or ["en"]

def detect_currencies(text: str) -> List[str]:
    return sorted(set(m.group(1).upper() for m in CURRENCY_RE.finditer(text)))

def detect_governing_law(text: str) -> List[str]:
    vals = []
    for m in GOV_LAW_RE.finditer(text):
        vals.append(m.group(2).strip())
    return list(dict.fromkeys(vals))  # uniq preserve order

def has_watermark(page: fitz.Page) -> List[str]:
    # heuristic: look for semi-transparent draw commands / common watermark words
    wm = []
    try:
        txt = page.get_text("text").lower()
        for key in ("confidential", "draft", "watermark"):
            if key in txt:
                wm.append(key)
    except Exception:
        pass
    return wm

def has_tables_pdfplumber(pl_page) -> bool:
    try:
        tables = pl_page.find_tables()
        return bool(tables)
    except Exception:
        return False

def clause_segment(text: str) -> List[ClauseOut]:
    # very light: split on obvious headings or blank lines followed by Capitalized
    lines = text.splitlines()
    clauses: List[ClauseOut] = []
    cur = []
    offsets: List[int] = []
    pos = 0
    for ln in lines:
        offsets.append(pos)
        pos += len(ln) + 1  # + newline
    # Identify headings by pattern: ALL CAPS line or line ending with '.'
    heads = []
    for i, ln in enumerate(lines):
        if ln.strip() and (ln.isupper() or re.match(r"^[A-Z][A-Za-z0-9 ,/&\-]{2,}$", ln.strip())):
            heads.append(i)
    if not heads:
        # single clause
        return [ClauseOut(id="C1", title=lines[0].strip()[:80] if lines else "Document",
                          heading=lines[0].strip() if lines else "Document",
                          start=0, end=len(text))]
    # build ranges
    for idx, start_i in enumerate(heads):
        end_i = heads[idx+1] if idx + 1 < len(heads) else len(lines)
        start_offset = offsets[start_i]
        end_offset = offsets[end_i-1] + len(lines[end_i-1]) + 1 if end_i-1 < len(offsets) else len(text)
        title = lines[start_i].strip()
        clauses.append(
            ClauseOut(
                id=f"C{idx+1}",
                title=title[:80] or f"Clause {idx+1}",
                heading=title or f"Clause {idx+1}",
                start=start_offset,
                end=end_offset
            )
        )
    return clauses


# ---------- Core service ----------

class ParsingOCRService:
    """
    Canonical entry: parse(file: Optional[UploadFile], path: Optional[str]) -> ParsingResultOut-like dict
    """

    def parse(self, file: Optional[UploadFile], path: Optional[str]):
        # Normalize input to a real path on disk
        tmp_path = None
        src_path = None

        if file is not None:
            suffix = ""
            if file.filename and "." in file.filename:
                suffix = os.path.splitext(file.filename)[1]
            with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                shutil.copyfileobj(file.file, tmp)
                tmp_path = tmp.name
                src_path = tmp_path
        elif path:
            src_path = path
        else:
            raise HTTPException(status_code=400, detail="Provide either an uploaded file or a filesystem path.")

        try:
            if not os.path.exists(src_path):
                raise HTTPException(status_code=404, detail=f"Path not found: {src_path}")

            ext = os.path.splitext(src_path)[1].lower()
            if ext in (".pdf",):
                result = self._parse_pdf(src_path)
            elif ext in (".docx",):
                result = self._parse_docx(src_path)
            elif ext in (".txt",):
                with open(src_path, "r", encoding="utf-8", errors="ignore") as fh:
                    txt = fh.read()
                result = self._postprocess_text(txt)
            else:
                raise HTTPException(status_code=415, detail=f"Unsupported file type: {ext}")

            # Shape to API schema dict
            return {
                "pages": [vars(p) for p in result.pages],
                "normalized_text": result.normalized_text,
                "clauses": [vars(c) for c in result.clauses],
                "meta": result.meta,
            }

        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    # ---------- Parsers ----------

    def _parse_pdf(self, path: str) -> ParsingResultOut:
        pages: List[PageOut] = []
        normalized_parts: List[str] = []

        with fitz.open(path) as doc:
            try:
                with pdfplumber.open(path) as pl:
                    plumber_pages = pl.pages
            except Exception:
                plumber_pages = [None] * len(doc)

            for i, page in enumerate(doc, start=1):
                rotation = int(page.rotation or 0)
                text = page.get_text("text") or ""
                ocr_used = False
                has_tables = False

                # If no text, try OCR
                if not text.strip() and Image and pytesseract:
                    pix = page.get_pixmap(dpi=200, alpha=False)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    text = pytesseract.image_to_string(img)
                    ocr_used = True

                # Tables (heuristic via pdfplumber if available)
                if plumber_pages and plumber_pages[i-1] is not None:
                    has_tables = has_tables_pdfplumber(plumber_pages[i-1])

                watermarks = has_watermark(page)
                # Quality score: simple heuristic on density & OCR flag
                q = min(1.0, 0.4 + 0.0005 * len(text)) - (0.1 if ocr_used else 0.0)
                q = round(max(0.0, q), 3)

                pages.append(PageOut(
                    page_number=i,
                    text=text.strip(),
                    ocr_used=ocr_used,
                    rotation=rotation,
                    has_tables=has_tables,
                    watermarks=watermarks,
                    quality_score=q
                ))
                normalized_parts.append(text.strip())

        normalized_text = ("\n\n".join(p.text for p in pages) + "\n").strip()

        clauses = clause_segment(normalized_text)
        meta = {
            "governing_law": detect_governing_law(normalized_text),
            "jurisdiction": [],  # stub
            "languages": detect_languages(normalized_text),
            "currencies": detect_currencies(normalized_text),
        }
        return ParsingResultOut(pages=pages, normalized_text=normalized_text, clauses=clauses, meta=meta)

    def _parse_docx(self, path: str) -> ParsingResultOut:
        if Document is None:
            raise HTTPException(status_code=500, detail="python-docx not installed")
        doc = Document(path)
        texts = []
        for p in doc.paragraphs:
            t = p.text.strip()
            if t:
                texts.append(t)
        body = "\n".join(texts)
        # Single-page model for DOCX
        page = PageOut(
            page_number=1,
            text=body,
            ocr_used=False,
            rotation=0,
            has_tables=False,   # basic; enhancing with python-docx tables is possible
            watermarks=[],
            quality_score=1.0 if len(body) > 0 else 0.0
        )
        normalized_text = body
        clauses = clause_segment(normalized_text)
        meta = {
            "governing_law": detect_governing_law(normalized_text),
            "jurisdiction": [],
            "languages": detect_languages(normalized_text),
            "currencies": detect_currencies(normalized_text),
        }
        return ParsingResultOut(pages=[page], normalized_text=normalized_text, clauses=clauses, meta=meta)

    def _postprocess_text(self, text: str) -> ParsingResultOut:
        t = text.strip()
        page = PageOut(
            page_number=1,
            text=t,
            ocr_used=False,
            rotation=0,
            has_tables=False,
            watermarks=[],
            quality_score=1.0 if len(t) > 0 else 0.0
        )
        normalized_text = t + ("\n" if not t.endswith("\n") else "")
        clauses = clause_segment(normalized_text)
        meta = {
            "governing_law": detect_governing_law(normalized_text),
            "jurisdiction": [],
            "languages": detect_languages(normalized_text),
            "currencies": detect_currencies(normalized_text),
        }
        return ParsingResultOut(pages=[page], normalized_text=normalized_text, clauses=clauses, meta=meta)
