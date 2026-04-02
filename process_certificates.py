#!/usr/bin/env python3
"""
Certificate Processing Workflow
================================
1. Reads certificate images from ./in/
2. Uses Claude API (vision) to extract certificate data
3. Inserts a CERTIFICATION line into README.md
4. Moves the image to ./done/
5. Re-reads README.md to verify the entry was added
"""

import base64
import os
import re
import shutil
import sys
from pathlib import Path

import anthropic

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
IN_DIR = Path("in")
DONE_DIR = Path("done")
CV_FILE = Path("README.md")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# The insertion anchor: new certifications go right before POST-DOCTORAL TRAINING
INSERT_BEFORE_PATTERN = re.compile(r"^POST-DOCTORAL TRAINING", re.MULTILINE)

# Detect duplicate: exact line already in the file
def _cert_line_exists(cv_text: str, cert_line: str) -> bool:
    return cert_line.strip() in cv_text


# ---------------------------------------------------------------------------
# Step 1 – extract certificate info via Claude vision
# ---------------------------------------------------------------------------
def extract_certificate_info(client: anthropic.Anthropic, image_path: Path) -> dict:
    """Return a dict with keys: title, issuer, date, recipient (all strings)."""
    suffix = image_path.suffix.lower()
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_type_map.get(suffix, "image/jpeg")

    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    prompt = (
        "You are reading a certificate image. Extract the following fields exactly as they appear:\n"
        "1. Certificate title / name of certification\n"
        "2. Issuing organization\n"
        "3. Date issued (month and year if available, otherwise just year)\n"
        "4. Recipient name (if visible)\n\n"
        "Respond in this exact format (one field per line, no extra text):\n"
        "TITLE: <value>\n"
        "ISSUER: <value>\n"
        "DATE: <value>\n"
        "RECIPIENT: <value>\n"
        "If a field is not visible, write N/A for that field."
    )

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    raw = response.content[0].text
    fields = {}
    for line in raw.splitlines():
        for key in ("TITLE", "ISSUER", "DATE", "RECIPIENT"):
            if line.startswith(f"{key}:"):
                fields[key.lower()] = line[len(key) + 1:].strip()

    # Provide defaults for missing keys
    for key in ("title", "issuer", "date", "recipient"):
        fields.setdefault(key, "N/A")

    return fields


# ---------------------------------------------------------------------------
# Step 2 – format as a CV CERTIFICATION line
# ---------------------------------------------------------------------------
def format_cert_line(info: dict) -> str:
    parts = ["CERTIFICATION"]
    if info["title"] != "N/A":
        parts.append(info["title"])
    if info["issuer"] != "N/A":
        parts.append(f"- {info['issuer']}")
    if info["date"] != "N/A":
        parts.append(f"- {info['date']}")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Step 3 – insert line into README.md
# ---------------------------------------------------------------------------
def insert_certification(cv_path: Path, cert_line: str) -> bool:
    """Insert cert_line before POST-DOCTORAL TRAINING. Returns True if inserted."""
    text = cv_path.read_text(encoding="utf-8")

    if _cert_line_exists(text, cert_line):
        print(f"  [skip] Already present in CV: {cert_line}")
        return False

    match = INSERT_BEFORE_PATTERN.search(text)
    if not match:
        # Fallback: append to end of file
        print("  [warn] Could not find POST-DOCTORAL TRAINING anchor; appending to end.")
        new_text = text.rstrip("\n") + "\n" + cert_line + "\n"
    else:
        insert_pos = match.start()
        new_text = text[:insert_pos] + cert_line + "\n" + text[insert_pos:]

    cv_path.write_text(new_text, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Step 4 – move image to done/
# ---------------------------------------------------------------------------
def move_to_done(image_path: Path) -> Path:
    DONE_DIR.mkdir(parents=True, exist_ok=True)
    dest = DONE_DIR / image_path.name
    # Avoid overwriting an existing file in done/
    if dest.exists():
        stem = image_path.stem
        suffix = image_path.suffix
        counter = 1
        while dest.exists():
            dest = DONE_DIR / f"{stem}_{counter}{suffix}"
            counter += 1
    shutil.move(str(image_path), str(dest))
    return dest


# ---------------------------------------------------------------------------
# Step 5 – verify the entry is in the CV
# ---------------------------------------------------------------------------
def verify_in_cv(cv_path: Path, cert_line: str) -> bool:
    text = cv_path.read_text(encoding="utf-8")
    return cert_line.strip() in text


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    IN_DIR.mkdir(parents=True, exist_ok=True)
    DONE_DIR.mkdir(parents=True, exist_ok=True)

    images = [
        p for p in IN_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]

    if not images:
        print(f"No certificate images found in {IN_DIR}/  (supported: {', '.join(IMAGE_EXTENSIONS)})")
        sys.exit(0)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable is not set.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    all_ok = True
    for image_path in sorted(images):
        print(f"\nProcessing: {image_path.name}")

        # 1. Extract info
        print("  Extracting certificate data via Claude vision...")
        info = extract_certificate_info(client, image_path)
        print(f"  Title    : {info['title']}")
        print(f"  Issuer   : {info['issuer']}")
        print(f"  Date     : {info['date']}")
        print(f"  Recipient: {info['recipient']}")

        # 2. Format CV line
        cert_line = format_cert_line(info)
        print(f"  CV line  : {cert_line}")

        # 3. Insert into CV
        inserted = insert_certification(CV_FILE, cert_line)
        if inserted:
            print(f"  Inserted into {CV_FILE}")

        # 4. Move to done/
        dest = move_to_done(image_path)
        print(f"  Moved to : {dest}")

        # 5. Verify
        if verify_in_cv(CV_FILE, cert_line):
            print(f"  [OK] Verified: entry found in {CV_FILE}")
        else:
            print(f"  [FAIL] Verification failed: entry NOT found in {CV_FILE}")
            all_ok = False

    if all_ok:
        print("\nAll certificates processed and verified successfully.")
    else:
        print("\nSome verifications failed. Please check the CV manually.")
        sys.exit(1)


if __name__ == "__main__":
    main()
