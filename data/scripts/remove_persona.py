#!/usr/bin/env python3
"""Remove a persona from the training corpora — by SPEAKER, never by substring.

A naive `grep -v epicurus` would delete hundreds of legitimate Seneca rows, because
Seneca quotes Epicurus constantly in the Letters. Those quotations are authentic Seneca
voice and must survive. This script only removes rows where the persona is the one
SPEAKING, determined from the DPO `persona` field or the "You are <Name>," system prompt.

Usage:
    python3 remove_persona.py epicurus            # dry run, prints what would change
    python3 remove_persona.py epicurus --apply    # rewrite files in place
"""
import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "training-data", "stoic_persona")


def persona_of(obj):
    """Who is SPEAKING in this row? None if undeterminable."""
    if "persona" in obj:
        return str(obj["persona"]).lower()
    for key, role_key, text_key in (("conversations", "from", "value"),
                                    ("messages", "role", "content")):
        seq = obj.get(key)
        if seq and seq[0].get(role_key) in ("system",):
            m = re.match(r"You are (.+?),", seq[0][text_key])
            if m:
                return re.sub(r"^the\s+", "", m.group(1).lower()).replace(" ", "_")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("persona", help="persona key, e.g. epicurus")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--data-dir", default=DATA_DIR)
    args = ap.parse_args()
    key = args.persona.lower()

    files = []
    for root, _dirs, names in os.walk(args.data_dir):
        for n in sorted(names):
            if n.endswith(".jsonl"):
                files.append(os.path.join(root, n))
    if not files:
        sys.exit(f"No .jsonl files under {args.data_dir}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = os.path.join(args.data_dir, f"_removed_{key}_{stamp}")

    print(f"{'file':<54} {'rows':>7} {'spoken':>7} {'mentions':>9} {'-> kept':>8}")
    print("-" * 90)
    total_removed = total_mentions = 0
    plan = []
    for f in files:
        rows = kept = spoken = mentions = 0
        keep_lines = []
        for line in open(f):
            if not line.strip():
                continue
            rows += 1
            obj = json.loads(line)
            p = persona_of(obj)
            if p and key in p:
                spoken += 1
                continue
            if key in line.lower():
                mentions += 1          # another persona quoting them - PRESERVED
            keep_lines.append(line)
            kept += 1
        total_removed += spoken
        total_mentions += mentions
        rel = os.path.relpath(f, args.data_dir)
        whole = spoken == rows and rows > 0
        note = "  <- whole file" if whole else ""
        if spoken:
            print(f"{rel:<54} {rows:>7} {spoken:>7} {mentions:>9} {kept:>8}{note}")
            plan.append((f, keep_lines, whole))

    print("-" * 90)
    print(f"rows to remove (spoken by {key}): {total_removed}")
    print(f"rows PRESERVED that merely mention {key}: {total_mentions}")

    if not args.apply:
        print("\nDry run. Re-run with --apply to write changes.")
        return

    os.makedirs(backup_root, exist_ok=True)
    for f, keep_lines, whole in plan:
        rel = os.path.relpath(f, args.data_dir)
        dest = os.path.join(backup_root, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(f, dest)
        if whole:
            os.remove(f)
        else:
            with open(f, "w") as fh:
                fh.writelines(keep_lines)
    manifest = {
        "persona_removed": key,
        "timestamp": stamp,
        "rows_removed": total_removed,
        "rows_preserved_mentioning": total_mentions,
        "files": [os.path.relpath(f, args.data_dir) for f, _, _ in plan],
        "note": "Removal is by SPEAKER. Rows where other personas quote this one are kept.",
    }
    with open(os.path.join(backup_root, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"\nApplied. Originals backed up to: {backup_root}")


if __name__ == "__main__":
    main()
