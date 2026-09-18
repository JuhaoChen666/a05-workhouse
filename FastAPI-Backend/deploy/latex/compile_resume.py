"""Fixed container entry point; no arbitrary executable or command input."""
import base64
import json
import hashlib
import re
import resource
import subprocess
import sys
from pathlib import Path, PurePosixPath

resource.setrlimit(resource.RLIMIT_FSIZE, (12 * 1024 * 1024, 12 * 1024 * 1024))
payload = json.loads(Path("/input.json").read_text(encoding="utf-8"))
source = payload["source"].encode("utf-8")
if len(source) > 2 * 1024 * 1024:
    raise ValueError("source too large")
Path("resume.tex").write_bytes(source)
total = 0
for name, value in payload.get("resources", {}).items():
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name or name in ("resume.tex", "resume.pdf"):
        raise ValueError("invalid resource")
    if value.get("encoding") != "base64":
        raise ValueError("invalid resource encoding")
    content = base64.b64decode(value["content"], validate=True)
    if len(content) != value.get("size_bytes") or hashlib.sha256(content).hexdigest() != value.get("sha256"):
        raise ValueError("invalid resource digest")
    total += len(content)
    if total > 32 * 1024 * 1024:
        raise ValueError("resources too large")
    target = Path(*path.parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
environment = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/tmp", "TEXMFOUTPUT": "/work",
               "openin_any": "p", "openout_any": "p", "shell_escape": "f"}
with Path("compile.log").open("wb") as log:
    try:
        subprocess.run(["xelatex", "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error", "resume.tex"],
                       env=environment, stdout=log, stderr=subprocess.STDOUT, timeout=30, check=True)
    except subprocess.TimeoutExpired:
        print(json.dumps({"error": "COMPILE_TIMEOUT"}))
        sys.exit(0)
    except subprocess.CalledProcessError:
        log.flush()
        with Path("compile.log").open("rb") as reader:
            reader.seek(max(0, Path("compile.log").stat().st_size - 8192))
            error_line = re.search(rb"(?:^|\n)l\.(\d{1,6})\b", reader.read())
        events = Path("/sys/fs/cgroup/memory.events")
        oom = events.exists() and any(line.startswith("oom_kill ") and int(line.split()[1]) > 0 for line in events.read_text().splitlines())
        print(json.dumps({"error": "COMPILE_RESOURCE_LIMIT" if oom else "COMPILE_FAILED",
            "location": "line " + error_line.group(1).decode() if error_line else None}))
        sys.exit(0)
pdf = Path("resume.pdf").read_bytes()
print(json.dumps({"pdf": base64.b64encode(pdf).decode("ascii")}))
