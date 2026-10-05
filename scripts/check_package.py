"""Exercise an extracted portable ZIP, without source files or a Python runtime on PATH."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="Feudsolver portable test ") as temp:
        folder = Path(temp)
        with zipfile.ZipFile(args.archive) as archive:
            archive.extractall(folder)
        exe = folder / "Feudsolver" / ("Feudsolver.exe" if os.name == "nt" else "Feudsolver")
        if os.name != "nt":
            exe.chmod(0o755)
            (exe.parent / "bin/feudsolver").chmod(0o755)
        env = {key:value for key,value in os.environ.items() if not key.startswith(("FEUD_", "PYTHON"))}
        env.update({"PATH":"", "PORT":str(port), "FEUD_HOST":"127.0.0.1", "FEUD_OPEN_BROWSER":"0"})
        base = f"http://127.0.0.1:{port}"
        def request(path, data=None, content_type="application/json"):
            req = urllib.request.Request(base+path, data=data, headers={"Content-Type":content_type})
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read()
        log_path = folder / "application.log"
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen([str(exe)], cwd=folder, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                for _ in range(150):
                    if process.poll() is not None:
                        raise RuntimeError("Packaged app exited before startup")
                    try:
                        health = json.loads(request("/api/health"))
                        break
                    except (urllib.error.URLError, TimeoutError):
                        time.sleep(.2)
                else:
                    raise RuntimeError("Packaged app did not start within 30 seconds")
                assert health["engine_ready"] and health["dictionary_ready"], health
                assert not health["example_available"], "Personal screenshot must not be distributed"
                assert b"Feudsolver" in request("/")
                assert b"mobile-nav" in request("/mobile.css")
                sample = {"board":["."*15]*15, "rack":"ÖL"}
                result = json.loads(request("/api/solve", json.dumps(sample).encode("utf-8")))
                assert any(move["word"]=="ÖL" for move in result["moves"]), result
                # Exercise the bundled font, image libraries and engine through real HTTP.
                image = (ROOT / "IMG_3527.PNG").read_bytes()
                boundary = "feudsolver-package-test"
                body = (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="screenshot.png"\r\nContent-Type: image/png\r\n\r\n').encode()+image+f"\r\n--{boundary}--\r\n".encode()
                recognized = json.loads(request("/api/recognize", body, f"multipart/form-data; boundary={boundary}"))
                expected = json.loads((ROOT / "examples/screenshot.json").read_text(encoding="utf-8"))
                assert recognized["board"]==expected["board"] and recognized["rack"]==expected["rack"]
                solved = json.loads(request("/api/solve", json.dumps(recognized).encode()))
                assert solved["moves"] and solved["moves"][0]["word"]=="VARAR"
                print("Portable ZIP passed: independent startup, website, Swedish solve, image recognition and full-position solve.")
            except Exception:
                log.flush()
                print(log_path.read_text(encoding="utf-8"))
                raise
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == "__main__":
    main()
