import argparse
import yaml
from jsonschema import validate, Draft202012Validator
from policies.validators import load_yaml

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", required=True)
    ap.add_argument("--schema", required=True)
    args = ap.parse_args()

    policy = load_yaml(args.policy)
    schema = load_yaml(args.schema)

    v = Draft202012Validator(schema)
    errors = sorted(v.iter_errors(policy), key=lambda e: e.path)
    if errors:
        for e in errors:
            print(f"[ERROR] {'/'.join([str(p) for p in e.path])}: {e.message}")
        raise SystemExit(1)
    print("✅ Policy validates against schema.")

if __name__ == "__main__":
    main()
