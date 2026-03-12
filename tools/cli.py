#!/usr/bin/env python3
"""Interactive CLI for selecting FinanceBench company groups and exporting to Langfuse format."""

import json
import sys
from pathlib import Path

# Ensure tools/ is on the path for sibling imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pick import pick

import data_loader
import langfuse_exporter

PROJECT_ID_CACHE = Path(__file__).resolve().parent.parent / "data" / "project_id_cache.json"


def load_project_id_cache():
    if PROJECT_ID_CACHE.exists():
        return json.loads(PROJECT_ID_CACHE.read_text())
    return {}


def save_project_id_cache(cache):
    PROJECT_ID_CACHE.write_text(json.dumps(cache, indent=2))


def build_options(company_groups):
    """Build display options for the pick multi-select menu."""
    # Collect all question types across all companies
    all_types = sorted({
        qa.get("question_type", "unknown")
        for group in company_groups.values()
        for qa in group["qa_pairs"]
    })

    # First pass: collect all row data
    rows = []
    for company, group in company_groups.items():
        doc_types = ", ".join(sorted({d["doc_type"] for d in group["documents"]}))
        page_counts = [d["page_count"] for d in group["documents"] if d["page_count"] is not None]
        total_pages = sum(page_counts)

        type_counts = {t: 0 for t in all_types}
        for qa in group["qa_pairs"]:
            t = qa.get("question_type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
        type_summary = ", ".join(f"{t}: {'🌵' if c == 0 else c}" for t, c in sorted(type_counts.items()))

        rows.append((company, len(group["documents"]), total_pages, group["num_questions"], type_summary, doc_types))

    rows.sort(key=lambda r: r[2])

    # Compute column widths
    w_company  = max(len(r[0]) for r in rows)
    w_docs     = max(len(str(r[1])) for r in rows)
    w_pages    = max(len(str(r[2])) for r in rows)
    w_qa       = max(len(str(r[3])) for r in rows)
    w_types    = max(len(r[4]) for r in rows)

    options = []
    for company, n_docs, total_pages, n_qa, type_summary, doc_types in rows:
        label = (
            f"{company:<{w_company}}  "
            f"{n_docs:>{w_docs}} docs  "
            f"{total_pages:>{w_pages}} pages  "
            f"{n_qa:>{w_qa}} Q&A  "
            f"[{type_summary:<{w_types}}]  "
            f"({doc_types})"
        )
        options.append((label, company))
    return options


def main():
    print("Loading FinanceBench data...")
    company_groups = data_loader.get_company_groups()
    print(f"Found {len(company_groups)} companies.\n")

    options = build_options(company_groups)
    display_options = [opt[0] for opt in options]

    title = "Select companies for Langfuse export (SPACE to toggle, ENTER to confirm):"
    selected = pick(display_options, title, multiselect=True, min_selection_count=1)

    # selected is list of (label, index) tuples
    selected_companies = [options[idx][1] for _, idx in selected]

    # Prompt for project_id for each company
    project_id_cache = load_project_id_cache()
    project_ids = {}
    print()
    for company in selected_companies:
        cached = project_id_cache.get(company)
        if cached:
            answer = input(f"Project ID for {company} [{cached}]: ").strip()
            project_id = answer if answer else cached
        else:
            project_id = input(f"Enter project ID for {company}: ").strip()
        if not project_id:
            print(f"Error: project ID is required for {company}")
            sys.exit(1)
        project_ids[company] = project_id
        project_id_cache[company] = project_id
    save_project_id_cache(project_id_cache)

    print(f"\nExporting {len(selected_companies)} companies...")
    results = langfuse_exporter.export(selected_companies, company_groups, project_ids)

    print("\nExport complete!")
    print(f"Output directory: {langfuse_exporter.OUTPUT_DIR}\n")
    for entry in results:
        print(f"  {entry['company']} [Evaluation]: {entry['num_questions']} Q&A pairs → {entry['file']}")
        print(f"    Documents: {', '.join(entry['documents'])}")
    print(f"\nManifest written to: {langfuse_exporter.OUTPUT_DIR / 'manifest.json'}")


if __name__ == "__main__":
    main()
