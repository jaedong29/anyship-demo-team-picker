"""Check deploy-spec.yaml with AnyShip's AI JSON Schema and the infra parse_spec.

usage: python scripts/check_spec.py [ANYSHIP_CLONE]   (default: ../anyship next to this repo)
"""
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
anyship = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT.parent / "anyship"
schema_path = anyship / "AI" / "ai" / "src" / "ai" / "spec" / "schema.json"
adapters = anyship / "infra" / "adapters"
if not schema_path.is_file() or not adapters.is_dir():
    sys.exit(f"AnyShip 저장소를 찾지 못했습니다: {anyship}")
sys.path.insert(0, str(adapters))
from anyship_adapters.spec import SpecError, parse_spec

spec = yaml.safe_load((ROOT / "deploy-spec.yaml").read_text(encoding="utf-8"))
schema = json.loads(schema_path.read_text(encoding="utf-8"))
errors = sorted(error.message for error in Draft202012Validator(schema).iter_errors(spec))
print("source.repo:", spec.get("source", {}).get("repo"))
print("AI JSON Schema:", "OK" if not errors else errors)
try:
    parsed = parse_spec(spec)
    print("infra parse_spec: OK", f"(app={parsed.app}, port={parsed.port}, healthcheck={parsed.healthcheck})")
except SpecError as exc:
    print("infra parse_spec: 거부 -", exc.error.message)
    sys.exit(1)
sys.exit(1 if errors else 0)
