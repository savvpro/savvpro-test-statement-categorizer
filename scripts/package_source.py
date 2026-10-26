"""Build a source-only ZIP from Git-tracked files, with a SHA-256 manifest.

Run after adding the intended files to Git. Uses the working-tree bytes, not an
older commit; generated environments, local databases, and secrets are rejected.
"""

import argparse
import hashlib
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Destination ZIP outside this repository")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if output.is_relative_to(root):
        parser.error("Write the archive outside the source repository.")
    result = subprocess.run(["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True)
    names = [name for name in result.stdout.decode().split("\0") if name]
    if not names:
        parser.error("No tracked files. Add the intended source files to Git first.")
    forbidden = {"node_modules", ".venv", "data", "dist", "test-results", "playwright-report", "__pycache__"}
    manifest = []
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name in sorted(names):
            path = Path(name)
            if (
                forbidden.intersection(path.parts)
                or path.name.startswith(".env")
                or path.suffix in {".key", ".pem", ".sqlite3", ".db"}
            ):
                raise ValueError(f"Refusing to package generated/sensitive path: {name}")
            content = (root / path).read_bytes()
            archive.writestr(f"statement-categorizer/{name}", content)
            manifest.append(f"{hashlib.sha256(content).hexdigest()}  {name}")
        archive.writestr("statement-categorizer/MANIFEST.sha256", "\n".join(manifest) + "\n")
    with ZipFile(output) as archive:
        assert archive.testzip() is None
    print(f"Packaged {len(names)} source files plus a SHA-256 manifest into {output.name}.")


if __name__ == "__main__":
    main()
