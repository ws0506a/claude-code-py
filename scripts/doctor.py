"""Quick connectivity check: print effective config + try a minimal request."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Force UTF-8 output so the script doesn't crash on Windows cp936/GBK.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Mirror the loading logic from src/main.py
load_dotenv()
package_env = Path(__file__).resolve().parent.parent / ".env"
if package_env.is_file():
    load_dotenv(package_env, override=False)


def mask(value: str | None) -> str:
    if not value:
        return "(not set)"
    if len(value) <= 12:
        return value
    return f"{value[:8]}...{value[-4:]} (len={len(value)})"


api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL") or "(not set -> defaults to api.openai.com)"
model = os.getenv("QINGCODE_MODEL") or "(not set -> defaults to gpt-4.1-mini)"

print("=" * 60)
print("Effective configuration")
print("=" * 60)
print(f"  OPENAI_API_KEY  : {mask(api_key)}")
print(f"  OPENAI_BASE_URL : {base_url}")
print(f"  QINGCODE_MODEL  : {model}")
print(f"  cwd             : {os.getcwd()}")
print(f"  project .env    : {'found' if package_env.is_file() else 'MISSING'} ({package_env})")
print()

if not api_key:
    print("[FAIL] OPENAI_API_KEY is not set anywhere. Cannot test.")
    sys.exit(1)

print("=" * 60)
print("Probing the API with one minimal request...")
print("=" * 60)

from openai import OpenAI

client = OpenAI(base_url=os.getenv("OPENAI_BASE_URL"), api_key=api_key)
try:
    resp = client.chat.completions.create(
        model=os.getenv("QINGCODE_MODEL") or "gpt-4.1-mini",
        messages=[{"role": "user", "content": "ping"}],
        max_tokens=5,
    )
    print(f"[OK] OK — model replied: {resp.choices[0].message.content!r}")
except Exception as e:
    print(f"[FAIL] FAIL — {type(e).__name__}")
    msg = str(e)
    print(msg[:600] + ("..." if len(msg) > 600 else ""))
