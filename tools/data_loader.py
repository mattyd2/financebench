"""Data loading and company grouping logic for FinanceBench sampling."""

import json
from collections import defaultdict
from pathlib import Path

import pypdf

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PDF_DIR = Path(__file__).resolve().parent.parent / "pdfs"
QA_FILE = DATA_DIR / "financebench_open_source.jsonl"
DOC_META_FILE = DATA_DIR / "financebench_document_information.jsonl"
PAGE_COUNT_CACHE = DATA_DIR / "page_count_cache.json"


def _load_page_count_cache():
    if PAGE_COUNT_CACHE.exists():
        return json.loads(PAGE_COUNT_CACHE.read_text())
    return {}


def _save_page_count_cache(cache):
    PAGE_COUNT_CACHE.write_text(json.dumps(cache, indent=2))


def get_page_count(doc_name, cache):
    if doc_name in cache:
        return cache[doc_name]
    pdf_path = PDF_DIR / f"{doc_name}.pdf"
    if not pdf_path.exists():
        return None
    with open(pdf_path, "rb") as f:
        reader = pypdf.PdfReader(f)
        count = len(reader.pages)
    cache[doc_name] = count
    return count


def _load_jsonl(path):
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_qa_pairs():
    return _load_jsonl(QA_FILE)


def load_doc_metadata():
    return _load_jsonl(DOC_META_FILE)


def get_doc_metadata_map():
    """Returns a dict keyed by doc_name with metadata fields."""
    meta = load_doc_metadata()
    return {m["doc_name"]: m for m in meta}


def get_company_groups():
    """Group Q&A pairs and documents by company.

    Returns a dict keyed by company name:
    {
        "3M": {
            "documents": [{"doc_name": ..., "doc_type": ..., "doc_period": ..., "gics_sector": ...}, ...],
            "qa_pairs": [<full qa record>, ...],
            "num_questions": int,
        },
        ...
    }
    """
    qa_pairs = load_qa_pairs()
    doc_meta = get_doc_metadata_map()

    # Build a map of all docs per company from the metadata file
    all_company_docs = defaultdict(set)
    for doc_name, meta in doc_meta.items():
        company = meta.get("company")
        if company:
            all_company_docs[company].add(doc_name)

    groups = defaultdict(lambda: {"doc_names": set(), "qa_pairs": [], "documents": []})

    for qa in qa_pairs:
        company = qa["company"]
        groups[company]["qa_pairs"].append(qa)
        # Include all docs for this company, not just the one referenced by the Q&A pair
        groups[company]["doc_names"] = all_company_docs[company]

    cache = _load_page_count_cache()
    cache_dirty = False

    result = {}
    for company in sorted(groups.keys()):
        g = groups[company]
        docs = []
        for doc_name in sorted(g["doc_names"]):
            meta = doc_meta.get(doc_name, {})
            if doc_name not in cache:
                cache_dirty = True
            docs.append({
                "doc_name": doc_name,
                "doc_type": meta.get("doc_type", "unknown"),
                "doc_period": meta.get("doc_period"),
                "gics_sector": meta.get("gics_sector", "unknown"),
                "page_count": get_page_count(doc_name, cache),
            })
        result[company] = {
            "documents": docs,
            "qa_pairs": g["qa_pairs"],
            "num_questions": len(g["qa_pairs"]),
        }

    if cache_dirty:
        _save_page_count_cache(cache)

    return result
