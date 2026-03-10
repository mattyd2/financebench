#!/usr/bin/env python3
"""Interactive CLI for selecting FinanceBench company groups and exporting to Langfuse format."""

import sys
from pathlib import Path

# Ensure tools/ is on the path for sibling imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pick import pick

import data_loader
import langfuse_exporter


def build_options(company_groups):
    """Build display options for the pick multi-select menu."""
    options = []
    for company, group in company_groups.items():
        doc_types = ", ".join(sorted({d["doc_type"] for d in group["documents"]}))
        label = f"{company} — {len(group['documents'])} docs, {group['num_questions']} Q&A pairs ({doc_types})"
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

    print(f"\nExporting {len(selected_companies)} companies...")
    results = langfuse_exporter.export(selected_companies, company_groups)

    print("\nExport complete!")
    print(f"Output directory: {langfuse_exporter.OUTPUT_DIR}\n")
    for entry in results:
        print(f"  {entry['company']}: {entry['num_questions']} Q&A pairs → {entry['file']}")
        print(f"    Documents: {', '.join(entry['documents'])}")
    print(f"\nManifest written to: {langfuse_exporter.OUTPUT_DIR / 'manifest.json'}")


if __name__ == "__main__":
    main()
