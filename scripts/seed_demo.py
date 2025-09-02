import json
from pathlib import Path

DEMO = [
    {"_id": "D1", "title": "Governing Law", "text": "This Agreement shall be governed by the laws of New York."},
    {"_id": "D2", "title": "Limitation of Liability", "text": "Neither party shall be liable for indirect damages."},
    {"_id": "D3", "title": "Term and Termination", "text": "The term is 2 years with automatic renewal unless terminated."},
]

def main():
    base = Path("./data/acord")
    base.mkdir(parents=True, exist_ok=True)
    (base / "corpus.jsonl").write_text("\n".join(json.dumps(x) for x in DEMO), encoding="utf-8")
    (base / "queries.jsonl").write_text(
        "\n".join(json.dumps({"_id": f"Q{i+1}", "text": d["title"]}) for i, d in enumerate(DEMO)),
        encoding="utf-8",
    )
    (base / "qrels").mkdir(exist_ok=True)
    (base / "qrels" / "test.tsv").write_text("Q1\t0\tD1\t1\nQ2\t0\tD2\t1\nQ3\t0\tD3\t1\n", encoding="utf-8")
    print("Seeded demo ACORD corpus/queries/qrels.")

if __name__ == "__main__":
    main()
