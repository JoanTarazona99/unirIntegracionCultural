"""
Sources routes: expose the knowledge base for reading.

Foreign students can browse every official source that powers the RAG system,
read the full content, and translate it on demand into their own language.
"""

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_rag_module
from app.config.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

_BACKEND_DIR = Path(__file__).resolve().parents[3]
_I18N_DIR = _BACKEND_DIR.parent / "data" / "sources_i18n"

# Category + icon metadata keyed by source name (kept here so the document
# library stays focused on content). Category label is in Spanish; the frontend
# can translate it.
_SOURCE_META = {
    "КубГУ": ("Universidad", "🎓", "https://kubsu.ru"),
    "Стипендии": ("Universidad", "💰", "https://education-in-russia.com"),
    "Русский язык": ("Idioma", "🗣️", "https://kubsu.ru"),
    "Адаптация": ("Vida y cultura", "🌍", "https://kubsu.ru"),
    "МВД РФ": ("Migración", "🛂", "https://мвд.рф"),
    "ГУВМ МВД": ("Migración", "🛂", "https://мвд.рф/mvd/structure1/Glavnie_upravlenija/guvm"),
    "Госуслуги": ("Trámites en línea", "🖥️", "https://www.gosuslugi.ru"),
    "МФЦ": ("Trámites", "🏢", "https://mfc.krasnodar.ru"),
    "Документы РФ": ("Documentos", "📄", "https://www.nalog.gov.ru"),
    "Здравоохранение": ("Salud", "🏥", "https://www.rospotrebnadzor.ru"),
    "Банк": ("Finanzas", "🏦", "https://www.sberbank.ru"),
    "Транспорт": ("Transporte", "🚌", "https://transport.krd.ru"),
    "Мобильная связь": ("Comunicación", "📱", "https://www.mts.ru"),
    "Безопасность": ("Seguridad", "🚨", "https://мчс.рф"),
    "Жильё": ("Vivienda", "🏠", "https://kubsu.ru"),
    "Питание": ("Alimentación", "🍽️", "https://kubsu.ru"),
    "FAQ": ("Preguntas frecuentes", "❓", "https://kubsu.ru/faq"),
}


def _clean(text: str) -> str:
    """Normalize the triple-quoted indented content into clean lines."""
    lines = [ln.strip() for ln in (text or "").splitlines()]
    # Drop leading/trailing empty lines but keep internal blank lines.
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


@router.get("/api/sources")
async def get_sources(rag_module=Depends(get_rag_module)):
    """Return every knowledge-base source with its readable content."""
    try:
        library = rag_module.document_library
        names = library.list_sources()

        sources = []
        for name in names:
            doc = library.get_source(name) or {}
            category, icon, default_url = _SOURCE_META.get(
                name, ("Información", "📌", "https://kubsu.ru")
            )
            sections = [
                {"title": s.get("title", ""), "content": _clean(s.get("content", ""))}
                for s in doc.get("sections", [])
            ]
            sources.append(
                {
                    "id": name,
                    "name": name,
                    "title": doc.get("name", name),
                    "url": doc.get("url") or default_url,
                    "category": category,
                    "icon": icon,
                    "section_count": len(sections),
                    "sections": sections,
                }
            )

        # Preserve first-seen category order.
        categories = []
        for s in sources:
            if s["category"] not in categories:
                categories.append(s["category"])

        return {
            "count": len(sources),
            "categories": categories,
            "sources": sources,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting sources: {str(e)}")


_ALLOWED_LANGS = {"es", "en", "ru", "fr", "de", "zh", "ar", "vi", "hy", "kk", "pt", "it", "tr"}

# deep-translator language codes (differ from ours for some languages).
_DT_LANG = {
    "es": "spanish", "en": "english", "ru": "russian", "fr": "french",
    "de": "german", "zh": "chinese (simplified)", "ar": "arabic",
    "vi": "vietnamese", "hy": "armenian", "kk": "kazakh",
    "pt": "portuguese", "it": "italian", "tr": "turkish",
}


def _translate_text(text: str, lang: str) -> str:
    """Translate one block of text with deep-translator (chunked for length)."""
    from deep_translator import GoogleTranslator

    if not text or not text.strip():
        return text
    translator = GoogleTranslator(source="auto", target=_DT_LANG.get(lang, lang))
    # GoogleTranslator handles up to ~5000 chars; split long content by lines.
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


@router.get("/api/sources/{source_id}/translate")
async def translate_source(
    source_id: str,
    lang: str = Query(..., description="Target language code (es,en,ru,fr,zh,ar,vi,...)"),
    rag_module=Depends(get_rag_module),
):
    """Translate one source's sections into the target language.

    Uses deep-translator (fast, reliable) and caches the result to disk so each
    (source, language) pair is only translated once.
    """
    if lang not in _ALLOWED_LANGS:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {lang}")

    library = rag_module.document_library
    doc = library.get_source(source_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Source not found: {source_id}")

    # ---- Disk cache ----
    safe_id = "".join(c if c.isalnum() else "_" for c in source_id)
    cache_file = _I18N_DIR / f"{safe_id}__{lang}.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    try:
        sections_out = []
        for sec in doc.get("sections", []):
            title = sec.get("title", "")
            content = _clean(sec.get("content", ""))
            t_title = _translate_text(title, lang)
            t_content = _translate_text(content, lang)
            sections_out.append({"title": t_title.strip(), "content": t_content.strip()})
    except Exception as e:
        logger.warning("source_translation_failed", error=str(e))
        raise HTTPException(status_code=502, detail=f"Translation failed: {str(e)}")

    payload = {"id": source_id, "lang": lang, "sections": sections_out}

    try:
        _I18N_DIR.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        logger.warning("source_translation_cache_failed", error=str(e))

    return payload


