from pathlib import Path
from rich import print
from backend.app.core.path_resolver import acord_dir, cuad_dir

def count_jsonl_lines(p: Path) -> int:
    return sum(1 for _ in p.open("r", encoding="utf-8")) if p.exists() else 0

def main():
    acord = acord_dir()
    cuad = cuad_dir()
    print(f"[bold green]ACORD[/]: {acord}")
    print(f"[bold green]CUAD  [/]: {cuad}")

    # ACORD checks
    corpus = acord / "corpus.jsonl"
    queries = acord / "queries.jsonl"
    qrels_dir = acord / "qrels"
    print(f"corpus.jsonl: {corpus.exists()} ({count_jsonl_lines(corpus)} lines)")
    print(f"queries.jsonl: {queries.exists()} ({count_jsonl_lines(queries)} lines)")
    print(f"qrels dir: {qrels_dir.exists()}")

    # CUAD presence (we don't parse; just existence + sample subdir)
    full_txt = (cuad / "full_contract_txt")
    print(f"CUAD full_contract_txt dir exists: {full_txt.exists()}")

    print("[bold blue]Validation complete.[/]")

if __name__ == "__main__":
    main()
