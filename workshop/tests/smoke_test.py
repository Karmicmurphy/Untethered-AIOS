from pathlib import Path
import json, py_compile, tempfile
ROOT=Path(__file__).resolve().parents[1]
assert (ROOT/"app/index.html").exists()
assert (ROOT/"companion/server.py").exists()
assert (ROOT/"cloudflare/config.example.yml").exists()
assert (ROOT/"CURRENT_STATE.md").exists()
assert (ROOT/"companion/remote_access.py").exists()
assert (ROOT/"companion/visitor_bench.py").exists()
assert (ROOT/"docs/PROTOCOL_SECURITY.md").exists()
json.loads((ROOT/"app/modules/modules.json").read_text())
json.loads((ROOT/"skills/skills.json").read_text())
with tempfile.TemporaryDirectory(prefix="twis-smoke-") as temp_dir:
    py_compile.compile(str(ROOT/"companion/server.py"),cfile=str(Path(temp_dir)/"server.pyc"),doraise=True)
print("Twis Holo smoke test PASS")
