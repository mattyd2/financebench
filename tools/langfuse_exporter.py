"""Export selected company Q&A groups into Langfuse-ready CSV dataset files."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from data_loader import get_doc_metadata_map

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def _build_dataset_item(qa, doc_meta_map, project_id=None):
    """Convert a single Q&A record into a Langfuse dataset item."""
    doc_name = qa["doc_name"]
    meta = doc_meta_map.get(doc_name, {})

    evidence = []
    for ev in qa.get("evidence", []):
        evidence.append({
            "doc_name": ev.get("doc_name", doc_name),
            "evidence_page_num": ev.get("evidence_page_num"),
            "evidence_text": ev.get("evidence_text", ""),
        })

    metadata = {
        "financebench_id": qa["financebench_id"],
        "question_type": qa.get("question_type"),
        "question_reasoning": qa.get("question_reasoning"),
        "domain_question_num": qa.get("domain_question_num"),
        "doc_name": doc_name,
        "company": qa["company"],
        "doc_type": meta.get("doc_type"),
        "doc_period": meta.get("doc_period"),
        "gics_sector": meta.get("gics_sector"),
        "evidence": evidence,
    }

    if project_id:
        metadata["projectId"] = project_id

    return {
        "input": {"input": qa["question"]},
        "expected_output": {"expected_output": qa["answer"]},
        "metadata": {"metadata": metadata},
    }



def export(selected_companies, company_groups, project_ids=None):
    """Export Langfuse dataset CSV files for selected companies.

    Args:
        selected_companies: list of company names to export
        company_groups: dict from data_loader.get_company_groups()
        project_ids: optional dict mapping company names to project IDs

    Returns:
        list of dicts with export summary info per company
    """
    if project_ids is None:
        project_ids = {}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    doc_meta_map = get_doc_metadata_map()

    manifest_entries = []

    for company in selected_companies:
        group = company_groups[company]
        company_project_id = project_ids.get(company)
        items = [_build_dataset_item(qa, doc_meta_map, company_project_id) for qa in group["qa_pairs"]]

        # Sanitize company name for filename
        safe_name = company.replace(" ", "_").replace("/", "_").upper()
        out_path = OUTPUT_DIR / f"{safe_name}_langfuse_dataset.csv"

        # Write CSV file
        fieldnames = ["input", "expected_output", "metadata"]

        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for item in items:
                row = {
                    "input": json.dumps(item["input"]),
                    "expected_output": json.dumps(item["expected_output"]),
                    "metadata": json.dumps(item["metadata"]),
                }
                writer.writerow(row)

        manifest_entries.append({
            "company": company,
            "file": str(out_path.name),
            "num_questions": len(items),
            "documents": [d["doc_name"] for d in group["documents"]],
        })

    # Write manifest
    manifest = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "num_projects": len(manifest_entries),
        "projects": manifest_entries,
    }
    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest_entries
