"""Build a portable app for the current OS. Windows packages must be built on Windows."""
import argparse
import importlib.metadata
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import sysconfig

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-build", action="store_true", help="Use the existing compiled engine")
    args = parser.parse_args()
    if not args.skip_build:
        run("cmake", "-S", ".", "-B", "build", "-DCMAKE_BUILD_TYPE=Release")
        run("cmake", "--build", "build", "--config", "Release", "--parallel")
    suffix = ".exe" if sys.platform == "win32" else ""
    engine = next((path for path in [ROOT / f"build/Release/feudsolver{suffix}", ROOT / f"build/feudsolver{suffix}"] if path.is_file()), None)
    if engine is None:
        raise SystemExit("Compiled engine missing. Run setup before packaging.")
    if not (ROOT / "data/swedish.txt").is_file() or not (ROOT / "data/dictionary-source/license").is_file():
        run(sys.executable, "scripts/download_dictionary.py")

    run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--name", "Feudsolver",
        "--distpath", "dist", "--workpath", "build/pyinstaller", "--specpath", "build/pyinstaller",
        "--paths", str(ROOT), str(ROOT / "launcher.py"))
    folder = ROOT / "dist/Feudsolver"
    (folder / "bin").mkdir()
    shutil.copy2(engine, folder / "bin" / engine.name)
    shutil.copytree(ROOT / "web", folder / "web")
    shutil.copytree(ROOT / "data/fonts", folder / "data/fonts")
    shutil.copy2(ROOT / "data/swedish.txt", folder / "data/swedish.txt")
    # Include the unmodified LGPL dictionary and the transformation source.
    shutil.copytree(ROOT / "data/dictionary-source", folder / "data/dictionary-source")
    shutil.copy2(ROOT / "scripts/download_dictionary.py", folder / "data/dictionary-source/filter_source.py")
    (folder / "scripts").mkdir()
    for name in ("run.bat", "run.sh"):
        shutil.copy2(ROOT / "scripts" / name, folder / "scripts" / name)
    shutil.copy2(ROOT / "README.md", folder / "DEVELOPMENT.md")
    licenses = folder / "licenses"
    licenses.mkdir()
    shutil.copy2(ROOT / "engine/vendor/LICENSE.json", licenses / "nlohmann-json-MIT.txt")
    python_license = next((path for path in [Path(sys.base_prefix)/"LICENSE.txt", Path(sysconfig.get_path("stdlib"))/"LICENSE.txt", Path(sys.base_prefix)/"Resources/LICENSE.txt"] if path.is_file()), None)
    if python_license is None:
        raise SystemExit("Python license not found; use an official Python installation to build the package.")
    shutil.copy2(python_license, licenses / "Python-LICENSE.txt")
    # Preserve installed distribution notices without relying on PyInstaller hooks
    # to collect licensing files for transitive dependencies.
    for distribution in importlib.metadata.distributions():
        for file in distribution.files or []:
            if any(word in file.name.lower() for word in ("license", "copying", "notice")):
                source = Path(distribution.locate_file(file))
                if source.is_file() and source.suffix.lower() not in (".py", ".pyc", ".so", ".dll", ".pyd"):
                    target = licenses / distribution.metadata["Name"] / str(file).replace("../", "").replace("..\\", "")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    start = "Feudsolver.exe" if suffix else "./Feudsolver"
    (folder / "START-HERE.txt").write_text(
        f"Extract this entire folder first. Run {start}, or scripts/run{'.bat' if suffix else '.sh'}.\n"
        "No Python, CMake, or C++ compiler installation is required.\n"
        "The browser opens at http://localhost:8000. Keep the app window open.\n"
        "For a phone, use http://<computer-IP>:8000 on the same Wi-Fi.\n"
        "The C++ engine is in bin/. The website and dictionary must stay beside the application.\n"
        "PORT changes the server port; FEUD_HOST changes its network binding.\n"
        "FEUD_OPEN_BROWSER=0 disables opening a browser automatically.\n"
        "The DSSO dictionary differs from Wordfeud's official SAOL list.\n"
        "The example screenshot is not included. Upload your own screenshot.\n",
        encoding="utf-8",
    )
    system = {"win32": "windows", "darwin": "macos"}.get(sys.platform, sys.platform)
    arch = "x64" if platform.machine().lower() in ("amd64", "x86_64") else platform.machine().lower()
    archive = shutil.make_archive(str(ROOT / f"dist/Feudsolver-{system}-{arch}"), "zip", ROOT / "dist", "Feudsolver")
    print(f"Portable package: {archive}")


if __name__ == "__main__":
    main()
