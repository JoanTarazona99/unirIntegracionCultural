# -*- coding: utf-8 -*-
"""Генерация рисунков для курсовой работы (метрики оценки RAG-модуля)."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "figure.dpi": 150,
})

OUT = os.path.dirname(os.path.abspath(__file__))

# --- Реальные результаты эксперимента (data/eval/results/eval_20260701_040932.json) ---
MODES = ["Ключевой поиск", "BM25", "Гибридный"]
METRICS = {
    "Hit@5":       [0.3889, 0.6944, 0.9444],
    "Recall@5":    [0.2917, 0.6667, 0.9306],
    "MRR":         [0.3264, 0.5440, 0.7657],
    "nDCG@5":      [0.2728, 0.5545, 0.8010],
}
COLORS = ["#c0392b", "#e67e22", "#27ae60"]

# ---------- Рисунок 4: сравнение режимов поиска ----------
fig, ax = plt.subplots(figsize=(8.2, 4.6))
metric_names = list(METRICS.keys())
x = range(len(metric_names))
n = len(MODES)
width = 0.25
for i, mode in enumerate(MODES):
    vals = [METRICS[m][i] for m in metric_names]
    positions = [p + (i - (n - 1) / 2) * width for p in x]
    bars = ax.bar(positions, vals, width, label=mode, color=COLORS[i], edgecolor="black", linewidth=0.4)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.015, f"{v:.2f}",
                ha="center", va="bottom", fontsize=8)
ax.set_xticks(list(x))
ax.set_xticklabels(metric_names)
ax.set_ylim(0, 1.18)
ax.set_ylabel("Значение метрики")
ax.set_title("Сравнение режимов поиска информации (k = 5, 36 запросов)", pad=28)
ax.legend(loc="upper center", ncol=3, framealpha=0.9, bbox_to_anchor=(0.5, 1.10))
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig_modes.png"))
plt.close(fig)

# ---------- Рисунок 5: nDCG@5 по тематическим категориям ----------
CATS = ["Академ.", "Админ.", "Здоровье", "Жильё", "Язык", "Миграция", "Виза"]
CAT_KEY = ["academic", "admin", "health", "housing", "language", "migration", "visa"]
by_cat = {
    "keyword": {"academic": 0.0, "admin": 0.4786, "health": 0.1290, "housing": 0.25,
                "language": 0.5566, "migration": 0.2330, "visa": 0.2453},
    "bm25":    {"academic": 0.1052, "admin": 0.6454, "health": 0.9323, "housing": 0.75,
                "language": 0.9033, "migration": 0.2920, "visa": 0.6717},
    "hybrid":  {"academic": 0.6551, "admin": 0.7304, "health": 1.0, "housing": 0.9234,
                "language": 0.9799, "migration": 0.7812, "visa": 0.7422},
}
fig, ax = plt.subplots(figsize=(8.4, 4.8))
y = range(len(CATS))
height = 0.26
series = [("Ключевой поиск", "keyword", COLORS[0]),
          ("BM25", "bm25", COLORS[1]),
          ("Гибридный", "hybrid", COLORS[2])]
for i, (label, key, color) in enumerate(series):
    vals = [by_cat[key][c] for c in CAT_KEY]
    positions = [p + (i - (len(series) - 1) / 2) * height for p in y]
    ax.barh(positions, vals, height, label=label, color=color, edgecolor="black", linewidth=0.4)
ax.set_yticks(list(y))
ax.set_yticklabels(CATS)
ax.set_xlim(0, 1.05)
ax.set_xlabel("nDCG@5")
ax.set_title("Качество поиска по тематическим категориям (гибридный режим)")
ax.legend(loc="lower right", framealpha=0.9)
ax.invert_yaxis()
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig_categories.png"))
plt.close(fig)

# ---------- Рисунок 2 (замена ASCII): схема гибридного RAG-конвейера ----------
fig, ax = plt.subplots(figsize=(6.6, 8.6))
ax.set_xlim(0, 10)
ax.set_ylim(0, 20)
ax.axis("off")

def box(cx, cy, w, h, text, fc="#eaf2fb", ec="#2c6fbb"):
    b = FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                       boxstyle="round,pad=0.08,rounding_size=0.15",
                       fc=fc, ec=ec, lw=1.6)
    ax.add_patch(b)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=10, wrap=True)

def arrow(x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=16, lw=1.5, color="#333333"))

box(5, 19, 5.4, 1.2, "Запрос пользователя\n(ES / EN / RU)")
box(5, 17, 5.4, 1.2, "Предобработка и нормализация\n+ расширение синонимов", fc="#f4ecfb", ec="#8e44ad")
arrow(5, 18.4, 5, 17.6)

box(2.6, 14.6, 3.8, 1.4, "Разрежённый поиск\nBM25 (rank_bm25)", fc="#fdf0e6", ec="#e67e22")
box(7.4, 14.6, 3.8, 1.4, "Плотный поиск\nэмбеддинги MiniLM-L12\n(косинусная близость)", fc="#e9f7ef", ec="#27ae60")
arrow(5, 16.4, 2.9, 15.3)
arrow(5, 16.4, 7.1, 15.3)

box(5, 12.2, 6.2, 1.3, "Слияние ранжирований\nReciprocal Rank Fusion (k = 60)", fc="#fdeef0", ec="#c0392b")
arrow(2.6, 13.9, 4.4, 12.85)
arrow(7.4, 13.9, 5.6, 12.85)

box(5, 10.0, 6.2, 1.3, "Переранжирование\nCross-Encoder (mMiniLMv2)", fc="#eef3fb", ec="#2c6fbb")
arrow(5, 11.55, 5, 10.65)

box(5, 7.8, 6.2, 1.3, "Топ-k релевантных фрагментов\nбазы знаний", fc="#f7f7f7", ec="#555555")
arrow(5, 9.35, 5, 8.45)

box(5, 5.6, 6.2, 1.3, "Контроль достоверности\n(faithfulness ≥ 0.35, цитирование)", fc="#fef6e7", ec="#b8860b")
arrow(5, 7.15, 5, 6.25)

box(5, 3.4, 6.2, 1.3, "Языковая модель (Ollama)\nгенерация ответа с контекстом", fc="#f4ecfb", ec="#8e44ad")
arrow(5, 4.95, 5, 4.05)

box(5, 1.3, 6.2, 1.2, "Ответ с указанием источников", fc="#eaf2fb", ec="#2c6fbb")
arrow(5, 2.75, 5, 1.9)

fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig_rag_pipeline.png"), bbox_inches="tight")
plt.close(fig)

print("OK:", os.listdir(OUT))
