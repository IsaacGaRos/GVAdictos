#!/usr/bin/env python3
"""
Audit and inspect open topic validation findings.
Generates a detailed CSV export ordered by priority.
"""
import sys
import csv
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.db import connect

def audit_findings():
    with connect() as conn:
        # Get all open findings with topic metadata
        results = conn.execute("""
        SELECT
            t.topic_number,
            t.part,
            t.section,
            t.validation_status,
            tvf.finding_type,
            tvf.description,
            tvf.source,
            tvf.severity
        FROM topic_validation_findings tvf
        JOIN topics t ON tvf.topic_id = t.id
        WHERE tvf.status = 'abierto'
        ORDER BY
            CASE
                WHEN tvf.finding_type LIKE '%eurlex%' THEN 1
                WHEN tvf.finding_type LIKE '%delimitacion%' THEN 2
                WHEN tvf.finding_type LIKE '%doctrinal%' THEN 3
                ELSE 4
            END,
            t.topic_number,
            tvf.finding_type
        """).fetchall()

        # Print summary to console
        print(f"\n{'='*80}")
        print("OPEN VALIDATION FINDINGS AUDIT")
        print(f"{'='*80}\n")

        finding_types = {}
        for row in results:
            ftype = row[4]
            if ftype not in finding_types:
                finding_types[ftype] = []
            finding_types[ftype].append(row)

        for ftype in sorted(finding_types.keys()):
            count = len(finding_types[ftype])
            print(f"\n[{ftype.upper()}] — {count} findings")
            print("-" * 80)
            for row in finding_types[ftype]:
                topic_num, part, section, val_status, finding_type, desc, source, severity = row
                print(f"  Topic {topic_num} ({part}): {section}")
                print(f"    Status: {val_status} | Severity: {severity}")
                print(f"    {desc[:100]}")
                if source:
                    print(f"    Source: {source}")
                print()

        # Export to CSV
        output_path = Path(__file__).parent.parent / "data" / "reports" / "validation_findings_audit.csv"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'priority_order',
                'finding_type',
                'topic_number',
                'part',
                'section',
                'validation_status',
                'severity',
                'description',
                'source'
            ])

            priority_map = {
                'fuente_eurlex_pendiente': 1,
                'autentica_fuente_oficial_no_importada': 1,
                'delimitacion_articulos_pendiente': 2,
                'tema_doctrinal_pendiente': 3,
                'fuente_reglamentaria_pendiente': 4,
                'fuente_no_normativa_pendiente': 5,
                'fuente_europea_pendiente': 1,
            }

            for row in results:
                topic_num, part, section, val_status, finding_type, desc, source, severity = row
                priority = priority_map.get(finding_type, 99)
                writer.writerow([
                    priority,
                    finding_type,
                    topic_num,
                    part,
                    section,
                    val_status,
                    severity,
                    desc,
                    source or ''
                ])

        print(f"\n{'='*80}")
        print(f"Export saved: {output_path}")
        print(f"Total open findings: {len(results)}")
        print(f"{'='*80}\n")

if __name__ == '__main__':
    audit_findings()
