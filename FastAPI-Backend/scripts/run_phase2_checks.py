"""Project-only QA runner. Credentials use environment or a local masked prompt."""
import argparse
import getpass
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
from sqlalchemy.engine import URL


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mysql",action="store_true",help="Prompt locally for test connection if env is absent")
    parser.add_argument("--host",default="127.0.0.1")
    parser.add_argument("--port",type=int,default=3306)
    arguments = parser.parse_args()
    backend = Path(__file__).resolve().parents[1]
    project = backend.parent
    environment = dict(os.environ)
    if arguments.mysql and not environment.get("RESUME_TEST_MYSQL_URL"):
        username = input("MySQL test username: ").strip()
        if not username:
            raise SystemExit("Username is required; no credentials were guessed")
        password = getpass.getpass("MySQL test password (not logged): ")
        environment["RESUME_TEST_MYSQL_URL"] = URL.create("mysql+aiomysql",username=username,password=password,
            host=arguments.host,port=arguments.port,database="unused").render_as_string(hide_password=False)
    if not environment.get("RESUME_TEST_MYSQL_URL"):
        raise SystemExit("Set RESUME_TEST_MYSQL_URL locally or use --mysql for a masked prompt; real MySQL acceptance is required")
    environment["PYTHONPATH"] = str(backend)
    sys.path.insert(0,str(backend))
    from app.infrastructure.resume_template_store import safe_path
    temporary_root = safe_path(project / ".phase2-local")
    temporary_root.mkdir(exist_ok=True)
    # Newly generated name; never delete/rebuild an existing user directory.
    basetemp = temporary_root / ("pytest-" + uuid4().hex)
    if basetemp.exists() or temporary_root.resolve() != project / ".phase2-local":
        raise SystemExit("Unsafe test temporary path")
    print("Tests create and drop only their own random schema; supplied URL database is never migrated or cleared.")
    return subprocess.call([sys.executable,"-m","pytest",str(backend/"tests"),"--basetemp="+str(basetemp),
        "-o","cache_dir="+str(temporary_root/"cache"),"-q","-rs"],cwd=project,env=environment)


if __name__ == "__main__":
    raise SystemExit(main())
