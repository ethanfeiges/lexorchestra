"""List Gemini models (requires GEMINI_API_KEY)."""
import os
from pathlib import Path

for line in Path(".env").read_text(encoding="utf-8").splitlines():
    s = line.strip()
    if not s or s.startswith("#") or "=" not in s:
        continue
    k, _, v = s.partition("=")
    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
for m in client.models.list():
    name = getattr(m, "name", "")
    if "gemini" in name.lower() and "generate" in str(getattr(m, "supported_actions", "")).lower():
        print(name)
