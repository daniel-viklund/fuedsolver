"""Download the open DSSO spelling dictionary; this is NOT the official SAOL list."""
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]

def main():
    # Store the unmodified source and its license alongside the filtered word list.
    source = ROOT / "data/dictionary-source"
    source.mkdir(parents=True, exist_ok=True)
    base = "https://raw.githubusercontent.com/wooorm/dictionaries/main/dictionaries/sv/"
    for name in ("index.dic", "index.aff", "license", "readme.md"):
        with urllib.request.urlopen(base + name, timeout=60) as response:
            (source / name).write_bytes(response.read())
    words = set()
    for line in (source / "index.dic").read_text().splitlines():
        token = line.split()[0] if line.split() else ""
        word, _, flags = token.partition("/")
        # Exclude proper names, forbidden entries and stems requiring an affix.
        if any(flag in flags for flag in ("%", "¤", "c")) or not word.islower():
            continue
        if re.fullmatch(r"[a-pr-vxyzåäö]{2,15}", word):
            words.add(word.upper())
    if len(words) < 10000:
        raise RuntimeError("Unexpected dictionary format; refusing to install")
    (ROOT / "data/swedish.txt").write_text("\n".join(sorted(words)) + "\n")
    print(f"Installed {len(words):,} DSSO entries. Not SAOL; Hunspell affixes are not expanded.")

if __name__ == "__main__":
    main()
