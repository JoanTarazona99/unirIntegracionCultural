"""
One-time batch pre-translation of all knowledge-base sources.

Fills the on-disk cache (data/sources_i18n/) so the /api/sources/{id}/translate
endpoint serves instantly instead of translating on first request.

Usage (from backend/):
    python scripts/pretranslate_sources.py
    python scripts/pretranslate_sources.py --langs es en fr zh ar vi
    python scripts/pretranslate_sources.py --force   # re-translate existing
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# Console on Windows defaults to cp1252 and cannot print Cyrillic source names.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from enhanced_rag import OfficialDocumentLibrary  # noqa: E402

_I18N_DIR = _BACKEND_DIR.parent / "data" / "sources_i18n"

# Languages relevant to the main foreign-student populations at KubGU
# (Vietnam, China, Kazakhstan, Armenia, Syria, Egypt, Morocco, Nigeria + UI langs).
DEFAULT_LANGS = ["es", "en", "ru", "fr", "zh", "ar", "vi"]

_DT_LANG = {
    "es": "spanish", "en": "english", "ru": "russian", "fr": "french",
    "de": "german", "zh": "chinese (simplified)", "ar": "arabic",
    "vi": "vietnamese", "hy": "armenian", "kk": "kazakh",
    "pt": "portuguese", "it": "italian", "tr": "turkish",
}


def clean(text: str) -> str:
    lines = [ln.strip() for ln in (text or "").splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def translate_text(text: str, lang: str) -> str:
    from deep_translator import GoogleTranslator

    if not text or not text.strip():
        return text
    translator = GoogleTranslator(source="auto", target=_DT_LANG.get(lang, lang))
    if len(text) <= 4500:
        return translator.translate(text)
    parts, buf = [], ""
    for line in text.splitlines():
        if len(buf) + len(line) + 1 > 4500:
            parts.append(translator.translate(buf) if buf.strip() else buf)
            buf = ""
        buf += line + "\n"
    if buf:
        parts.append(translator.translate(buf) if buf.strip() else buf)
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--langs", nargs="+", default=DEFAULT_LANGS)
    parser.add_argument("--force", action="store_true", help="Re-translate existing caches")
    parser.add_argument("--delay", type=float, default=0.15, help="Delay between calls (s)")
    args = parser.parse_args()

    _I18N_DIR.mkdir(parents=True, exist_ok=True)
    library = OfficialDocumentLibrary()
    names = library.list_sources()

    total_pairs = len(names) * len(args.langs)
    done = 0
    calls = 0
    t_start = time.time()

    for name in names:
        doc = library.get_source(name) or {}
        safe_id = "".join(c if c.isalnum() else "_" for c in name)
        for lang in args.langs:
            done += 1
            cache_file = _I18N_DIR / f"{safe_id}__{lang}.json"
            if cache_file.exists() and not args.force:
                print(f"[{done}/{total_pairs}] skip {name} -> {lang} (cached)", flush=True)
                continue
            try:
                sections = []
                for sec in doc.get("sections", []):
                    t_title = translate_text(sec.get("title", ""), lang)
                    calls += 1
                    time.sleep(args.delay)
                    t_content = translate_text(clean(sec.get("content", "")), lang)
                    calls += 1
                    time.sleep(args.delay)
                    sections.append({"title": t_title.strip(), "content": t_content.strip()})
                payload = {"id": name, "lang": lang, "sections": sections}
                cache_file.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print(f"[{done}/{total_pairs}] OK   {name} -> {lang}", flush=True)
            except Exception as e:
                print(f"[{done}/{total_pairs}] FAIL {name} -> {lang}: {e}", flush=True)

    elapsed = time.time() - t_start
    print(f"\nDone. {calls} translation calls in {elapsed:.0f}s. Cache: {_I18N_DIR}", flush=True)


if __name__ == "__main__":
    main()
