import shutil
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
MANIFEST_FILE = BASE_DIR / "critical_files.txt"
UPLOAD_FOLDER = BASE_DIR / "mlb_critical_upload"

def prepare_upload_folder():
    if UPLOAD_FOLDER.exists():
        shutil.rmtree(UPLOAD_FOLDER)
    UPLOAD_FOLDER.mkdir()

    with open(MANIFEST_FILE, "r") as f:
        files = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    for file in files:
        src = BASE_DIR / file
        dest = UPLOAD_FOLDER / Path(file).name

        if not src.exists():
            print(f"❌ Missing: {file}")
            continue

        shutil.copy(src, dest)
        print(f"✅ Copied: {file}")

    # Open the folder in Finder (macOS)
    print(f"\n📂 Opening: {UPLOAD_FOLDER}")
    os.system(f"open {UPLOAD_FOLDER}")

if __name__ == "__main__":
    prepare_upload_folder()
