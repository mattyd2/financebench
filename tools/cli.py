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
    options = []
    for company, group in company_groups.items():
        doc_types = ", ".join(sorted({d["doc_type"] for d in group["documents"]}))
        page_counts = [d["page_count"] for d in group["documents"] if d["page_count"] is not None]
        total_pages = sum(page_counts)
        label = f"{company} — {len(group['documents'])} docs, {total_pages} pages, {group['num_questions']} Q&A pairs ({doc_types})"
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
