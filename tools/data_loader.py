"""Data loading and company grouping logic for FinanceBench sampling."""

import json
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
QA_FILE = DATA_DIR / "financebench_open_source.jsonl"
DOC_META_FILE = DATA_DIR / "financebench_document_information.jsonl"


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

    groups = defaultdict(lambda: {"doc_names": set(), "qa_pairs": [], "documents": []})

    for qa in qa_pairs:
        company = qa["company"]
        groups[company]["qa_pairs"].append(qa)
        groups[company]["doc_names"].add(qa["doc_name"])

    result = {}
    for company in sorted(groups.keys()):
        g = groups[company]
        docs = []
        for doc_name in sorted(g["doc_names"]):
            meta = doc_meta.get(doc_name, {})
            docs.append({
                "doc_name": doc_name,
                "doc_type": meta.get("doc_type", "unknown"),
                "doc_period": meta.get("doc_period"),
                "gics_sector": meta.get("gics_sector", "unknown"),
            })
        result[company] = {
            "documents": docs,
            "qa_pairs": g["qa_pairs"],
            "num_questions": len(g["qa_pairs"]),
        }

    return result
