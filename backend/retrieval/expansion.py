"""Versioned lexical query expansion for cross-lingual retrieval."""

from __future__ import annotations

from typing import Dict, List

from .chunks import tokenize


DEFAULT_EXPANSION_VERSION = "academic-es-en-ru-v1"

LEXICAL_EXPANSIONS: Dict[str, Dict[str, Dict[str, List[str]]]] = {
    DEFAULT_EXPANSION_VERSION: {
        "es": {
            "programas": ["программы"],
            "educación": ["образование"],
            "educacion": ["образование"],
            "cursos": ["курсы"],
            "admisión": ["поступление"],
            "admision": ["поступление"],
            "licenciatura": ["бакалавриат"],
            "posgrado": ["магистратура", "аспирантура"],
            "registro": ["регистрация", "регистрации"],
            "visa": ["виза", "визы", "визовый"],
            "migracion": ["миграция", "миграционная", "миграционной"],
            "dormitorio": ["общежитие", "общежития"],
            "vivienda": ["проживание", "жилье"],
            "profesor": ["преподаватель"],
            "clase": ["урок", "занятие"],
            "examen": ["экзамен", "экзамены"],
            "poliza": ["полис", "страхование"],
            "seguro": ["страхование", "полис"],
            "medico": ["медицинский", "врач"],
            "pasaporte": ["паспорт"],
            "documento": ["документ", "документы"],
            "estudiante": ["студент", "студентов"],
            "ruso": ["русский", "язык"],
            "mfc": ["мфц"],
            "costo": ["стоимость", "цена"],
        },
        "en": {
            "programs": ["программы"],
            "programmes": ["программы"],
            "education": ["образование"],
            "courses": ["курсы"],
            "admission": ["поступление"],
            "undergraduate": ["бакалавриат"],
            "bachelor": ["бакалавриат"],
            "postgraduate": ["магистратура", "аспирантура"],
            "graduate": ["магистратура", "аспирантура"],
            "registration": ["регистрация", "регистрации"],
            "visa": ["виза", "визы", "визовый"],
            "migration": ["миграция", "миграционная"],
            "dormitory": ["общежитие"],
            "housing": ["проживание", "жилье"],
            "exam": ["экзамен"],
            "insurance": ["страхование", "полис"],
            "medical": ["медицинский"],
            "passport": ["паспорт"],
            "document": ["документ", "документы"],
            "student": ["студент", "студентов"],
            "russian": ["русский", "язык"],
            "mfc": ["мфц"],
            "cost": ["стоимость", "цена"],
            "price": ["стоимость", "цена"],
        },
    }
}


def expand_query(
    query: str,
    source_language: str,
    target_language: str,
    *,
    version: str = DEFAULT_EXPANSION_VERSION,
) -> str:
    """Append mapped target-language terms while preserving the original query."""
    if version not in LEXICAL_EXPANSIONS:
        raise ValueError(f"Unknown lexical expansion version: {version}")
    if target_language.lower() not in {"ru", "rus", "russian"}:
        return query

    language = source_language.lower()
    tables = LEXICAL_EXPANSIONS[version]
    if language in {"auto", "unknown"}:
        selected_tables = list(tables.values())
    elif language in {"es", "spa", "spanish"}:
        selected_tables = [tables["es"]]
    elif language in {"en", "eng", "english"}:
        selected_tables = [tables["en"]]
    else:
        return query

    additions: List[str] = []
    seen = set(tokenize(query))
    for token in tokenize(query):
        for table in selected_tables:
            for translated_term in table.get(token, []):
                if translated_term not in seen:
                    additions.append(translated_term)
                    seen.add(translated_term)
    return " ".join([query.strip(), *additions]).strip()