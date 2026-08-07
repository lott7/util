import sys
from pathlib import Path

# Shared virtual environment that this .pth file targets.
SHARED_VENV_SITE_PACKAGES = Path(r"C:\Users\lott7\.venvs\py313\Lib\site-packages")

if not SHARED_VENV_SITE_PACKAGES.exists():
    sys.exit(
        f"Shared venv site-packages not found at {SHARED_VENV_SITE_PACKAGES}. "
        "Create it first (see A_Projects setup notes) before running this script."
    )

# Paths to make importable from anywhere in the shared env.
workspace_root = Path(__file__).parent.parent.parent
new_paths = [
    (workspace_root / "etf_rep_strat" / "src").resolve(),
    (workspace_root / "util" / "src").resolve(),
    (workspace_root / "eodhd_client" / "src").resolve(),
    (workspace_root / "alpha_engine" / "src").resolve(),
]

# Create/use your own .pth file
pth_file = SHARED_VENV_SITE_PACKAGES / "lott7_modules.pth"

# Read existing paths if the file exists
existing = set()
if pth_file.exists():
    existing = {
        line.strip()
        for line in pth_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }

# Create the file or append any missing paths
added = []
with pth_file.open("a", encoding="utf-8") as f:
    for new_path in new_paths:
        if str(new_path) not in existing:
            f.write(f"{new_path}\n")
            added.append(new_path)

if added:
    for path in added:
        print(f"Added {path} to {pth_file}")
else:
    print(f"All paths already present in {pth_file}")
