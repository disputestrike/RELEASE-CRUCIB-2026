import json
import shutil
import zipfile
from pathlib import Path

from backend.orchestration.import_doctor import (
    detect_framework,
    detect_package_manager,
    validate_imported_workspace,
    validate_zip_archive,
)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def case_root(name):
    root = Path(__file__).resolve().parents[2] / ".biv_test_tmp" / name
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_import_doctor_detects_react_vite_workspace():
    root = case_root("import_react_vite")
    write(
        root / "package.json",
        json.dumps(
            {
                "scripts": {"dev": "vite --host", "build": "vite build"},
                "dependencies": {"react": "latest", "vite": "latest"},
            }
        ),
    )
    write(root / "package-lock.json", "{}")
    write(root / "index.html", '<div id="root"></div>')
    write(root / "src" / "main.jsx", "import App from './App.jsx';")
    write(root / "src" / "App.jsx", "export default function App(){return <div>hello</div>}")

    files = {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in root.rglob("*")
        if path.is_file()
    }
    assert detect_package_manager(files) == "npm"
    assert detect_framework(files) == "react_vite"

    result = validate_imported_workspace(str(root), goal="Continue building this React app")
    assert result["framework"] == "react_vite"
    assert result["package_manager"] == "npm"
    assert result["entrypoints"]["react_main"]


def test_import_doctor_rejects_unsafe_zip_paths():
    root = case_root("import_zip")
    zip_path = root / "unsafe.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../evil.txt", "nope")
        zf.writestr("app/package.json", "{}")

    result = validate_zip_archive(str(zip_path))
    assert not result["passed"]
    assert any("Unsafe ZIP path" in issue for issue in result["issues"])
