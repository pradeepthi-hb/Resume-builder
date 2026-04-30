import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
IMPORT_SCRIPT = BACKEND_DIR / "database" / "import_csv.py"


def main():
    if not IMPORT_SCRIPT.exists():
        print(f"Missing script: {IMPORT_SCRIPT}")
        return 1

    print("Running CSV setup via import_csv.py...")
    try:
        subprocess.run([sys.executable, str(IMPORT_SCRIPT)], check=True, cwd=str(BACKEND_DIR))
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"Setup failed with exit code {exc.returncode}.")
        return exc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
