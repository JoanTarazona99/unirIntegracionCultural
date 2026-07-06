#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генерация профессиональных диаграмм архитектуры на русском языке.
Рисунки 1-3: Общая архитектура, детальная схема RAG, конвейер голоса
"""
import os
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "figure.dpi": 150,
})

def create_figure_1():
    """Архитектура: интерфейсы → бэкэнд → модули ИИ → данные"""
    fig, ax = plt.subplots(figsize=(11, 7.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    c_ui = "#e3f2fd"
    c_api = "#e8f5e9"
    c_ai = "#fff3e0"
    c_mm = "#fce4ec"
    c_data = "#f3e5f5"
    
    ax.text(5, 9.5, "Рисунок 1: Общая архитектура системы KubGU Assistant",
            ha='center', fontsize=12, fontweight='bold')
    
    # Веб-интерфейс
    rect_web = FancyBboxPatch((0.2, 7.5), 2, 1.2, boxstyle="round,pad=0.1",
                               edgecolor='#0066cc', facecolor=c_ui, linewidth=1.5)
    ax.add_patch(rect_web)
    ax.text(1.2, 8.3, "Веб-интерфейс", ha='center', fontsize=9, fontweight='bold')
    ax.text(1.2, 7.95, "Vue.js + HTML5", ha='center', fontsize=8)
    
    # Telegram-бот
    rect_tg = FancyBboxPatch((3, 7.5), 2, 1.2, boxstyle="round,pad=0.1",
                              edgecolor='#0066cc', facecolor=c_ui, linewidth=1.5)
    ax.add_patch(rect_tg)
    ax.text(4, 8.3, "Telegram-бот", ha='center', fontsize=9, fontweight='bold')
    ax.text(4, 7.95, "python-telegram-bot", ha='center', fontsize=8)
    
    # REST API FastAPI
    rect_api = FancyBboxPatch((0.2, 5.2), 7.6, 1.8, boxstyle="round,pad=0.1",
                               edgecolor='#2e7d32', facecolor=c_api, linewidth=2)
    ax.add_patch(rect_api)
    ax.text(4, 6.7, "REST API FastAPI (порт 8000)", ha='center', 
            fontsize=10, fontweight='bold')
    
    ax.text(1.5, 6.1, "API\nэндпоинты", ha='center', fontsize=8)
    ax.text(4, 6.1, "Аутентификация\n& Сессии", ha='center', fontsize=8)
    ax.text(6.5, 6.1, "Модуль\nконversации", ha='center', fontsize=8)
    
    # ЯМ: LLM
    rect_llm = FancyBboxPatch((0.2, 3), 1.8, 1.6, boxstyle="round,pad=0.1",
                               edgecolor='#ff6f00', facecolor=c_ai, linewidth=1.5)
    ax.add_patch(rect_llm)
    ax.text(1.1, 4.2, "ЯМ: LLM", ha='center', fontsize=9, fontweight='bold')
    ax.text(1.1, 3.8, "Qwen2.5\n7B-Instruct\nOllama", ha='center', fontsize=7)
    
    # RAG гибридный
    rect_rag = FancyBboxPatch((2.3, 3), 2.3, 1.6, boxstyle="round,pad=0.1",
                               edgecolor='#7b1fa2', facecolor=c_ai, linewidth=1.5)
    ax.add_patch(rect_rag)
    ax.text(3.45, 4.2, "RAG гибридный", ha='center', fontsize=9, fontweight='bold')
    ax.text(3.45, 3.75, "BM25 + Dense\nMiniLM\nRRF + Rerank", ha='center', fontsize=7)
    
    # Профиль
    rect_pers = FancyBboxPatch((4.8, 3), 1.8, 1.6, boxstyle="round,pad=0.1",
                                edgecolor='#d32f2f', facecolor=c_ai, linewidth=1.5)
    ax.add_patch(rect_pers)
    ax.text(5.7, 4.2, "Профиль", ha='center', fontsize=9, fontweight='bold')
    ax.text(5.7, 3.8, "Персонализ.\n& Рекомендации", ha='center', fontsize=7)
    
    # STT и TTS
    rect_stt = FancyBboxPatch((7, 3.2), 1.6, 0.7, boxstyle="round,pad=0.05",
                               edgecolor='#ff9800', facecolor=c_mm, linewidth=1.2)
    ax.add_patch(rect_stt)
    ax.text(7.8, 3.55, "STT: Whisper", ha='center', fontsize=8)
    
    rect_tts = FancyBboxPatch((7, 2.2), 1.6, 0.7, boxstyle="round,pad=0.05",
                               edgecolor='#ff9800', facecolor=c_mm, linewidth=1.2)
    ax.add_patch(rect_tts)
    ax.text(7.8, 2.55, "TTS: Web API", ha='center', fontsize=8)
    
    # База знаний
    rect_kb = FancyBboxPatch((0.2, 0.8), 3.5, 1.2, boxstyle="round,pad=0.1",
                              edgecolor='#388e3c', facecolor=c_data, linewidth=1.5)
    ax.add_patch(rect_kb)
    ax.text(2, 1.7, "База знаний", ha='center', fontsize=9, fontweight='bold')
    ax.text(2, 1.3, "КубГУ | МВД РФ | МФЦ | Госуслуги", ha='center', fontsize=7)
    
    # Redis Кэш
    rect_cache = FancyBboxPatch((4.2, 0.8), 3.6, 1.2, boxstyle="round,pad=0.1",
                                 edgecolor='#6f42c1', facecolor=c_data, linewidth=1.5)
    ax.add_patch(rect_cache)
    ax.text(6, 1.7, "Redis Кэш", ha='center', fontsize=9, fontweight='bold')
    ax.text(6, 1.3, "Ответы | Сессии | Индексы", ha='center', fontsize=7)
    
    # Стрелки
    arrow1 = FancyArrowPatch((1.2, 7.5), (1.5, 7.0), arrowstyle='->', 
                             mutation_scale=20, color='#333', linewidth=1.2)
    ax.add_patch(arrow1)
    arrow2 = FancyArrowPatch((4, 7.5), (4, 7.0), arrowstyle='->', 
                             mutation_scale=20, color='#333', linewidth=1.2)
    ax.add_patch(arrow2)
    
    for x in [1.1, 3.45, 5.7, 7.8]:
        arrow = FancyArrowPatch((x, 5.2), (x, 4.6), arrowstyle='->', 
                               mutation_scale=15, color='#666', linewidth=1)
        ax.add_patch(arrow)
    
    arrow_kb = FancyArrowPatch((3.45, 3), (2.5, 2.0), arrowstyle='<->', 
                              mutation_scale=15, color='#388e3c', linewidth=1.2, linestyle='--')
    ax.add_patch(arrow_kb)
    
    arrow_cache = FancyArrowPatch((3.45, 3), (6, 2.0), arrowstyle='<->', 
                                 mutation_scale=15, color='#6f42c1', linewidth=1.2, linestyle='--')
    ax.add_patch(arrow_cache)
    
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "fig_arquitectura.png"), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print("✓ Рисунок 1 сохранён: fig_arquitectura.png")

def create_figure_2():
    """RAG: Поиск + Генерация + Проверка достоверности"""
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    ax.text(6, 9.5, "Рисунок 2: Схема модуля RAG (Поиск + Генерация)",
            ha='center', fontsize=12, fontweight='bold')
    
    # Запрос пользователя
    rect_input = FancyBboxPatch((0.3, 8), 2.5, 0.8, boxstyle="round,pad=0.1",
                                 edgecolor='#000', facecolor='#e1f5fe', linewidth=1.5)
    ax.add_patch(rect_input)
    ax.text(1.55, 8.4, "Запрос пользователя", ha='center', fontsize=9, fontweight='bold')
    
    # Предобработка
    rect_prep = FancyBboxPatch((0.3, 6.5), 2.5, 1.2, boxstyle="round,pad=0.1",
                                edgecolor='#1976d2', facecolor='#e3f2fd', linewidth=1.2)
    ax.add_patch(rect_prep)
    ax.text(1.55, 7.4, "Предобработка", ha='center', fontsize=8, fontweight='bold')
    ax.text(1.55, 7.0, "Нормализация\nРасширение запроса", ha='center', fontsize=7)
    
    arrow_prep = FancyArrowPatch((1.55, 8.0), (1.55, 7.7), arrowstyle='->', 
                                mutation_scale=15, color='#333', linewidth=1.2)
    ax.add_patch(arrow_prep)
    
    # BM25 (Лексика)
    rect_bm25 = FancyBboxPatch((0.1, 4.5), 2, 1.5, boxstyle="round,pad=0.1",
                                edgecolor='#d32f2f', facecolor='#ffebee', linewidth=1.2)
    ax.add_patch(rect_bm25)
    ax.text(1.1, 5.7, "BM25 (Лексика)", ha='center', fontsize=8, fontweight='bold')
    ax.text(1.1, 5.2, "Поиск по\nключевым словам", ha='center', fontsize=7)
    
    arrow_bm25 = FancyArrowPatch((1.3, 6.5), (1.1, 6.0), arrowstyle='->', 
                                mutation_scale=15, color='#d32f2f', linewidth=1.2)
    ax.add_patch(arrow_bm25)
    
    # Плотный поиск
    rect_dense = FancyBboxPatch((2.3, 4.5), 2, 1.5, boxstyle="round,pad=0.1",
                                 edgecolor='#7b1fa2', facecolor='#f3e5f5', linewidth=1.2)
    ax.add_patch(rect_dense)
    ax.text(3.3, 5.7, "Плотный поиск", ha='center', fontsize=8, fontweight='bold')
    ax.text(3.3, 5.2, "MiniLM (384-dim)\nСемантика", ha='center', fontsize=7)
    
    arrow_dense = FancyArrowPatch((1.8, 6.5), (3.3, 6.0), arrowstyle='->', 
                                 mutation_scale=15, color='#7b1fa2', linewidth=1.2)
    ax.add_patch(arrow_dense)
    
    # RRF слияние
    rect_rrf = FancyBboxPatch((0.7, 3), 2.5, 0.9, boxstyle="round,pad=0.1",
                               edgecolor='#f57c00', facecolor='#ffe0b2', linewidth=1.2)
    ax.add_patch(rect_rrf)
    ax.text(1.95, 3.45, "RRF слияние", ha='center', fontsize=8, fontweight='bold')
    
    arrow_rrf1 = FancyArrowPatch((1.1, 4.5), (1.7, 3.9), arrowstyle='->', 
                                mutation_scale=12, color='#666', linewidth=1)
    ax.add_patch(arrow_rrf1)
    arrow_rrf2 = FancyArrowPatch((3.3, 4.5), (2.3, 3.9), arrowstyle='->', 
                                mutation_scale=12, color='#666', linewidth=1)
    ax.add_patch(arrow_rrf2)
    
    # Cross-encoder
    rect_rerank = FancyBboxPatch((3.5, 1.5), 2.2, 1.2, boxstyle="round,pad=0.1",
                                  edgecolor='#ff6f00', facecolor='#fff3e0', linewidth=1.2)
    ax.add_patch(rect_rerank)
    ax.text(4.6, 2.4, "Cross-encoder", ha='center', fontsize=8, fontweight='bold')
    ax.text(4.6, 2.0, "Переранжирование\n(Точность)", ha='center', fontsize=7)
    
    arrow_rerank = FancyArrowPatch((1.95, 3.0), (4.6, 2.7), arrowstyle='->', 
                                  mutation_scale=15, color='#ff6f00', linewidth=1.2)
    ax.add_patch(arrow_rerank)
    
    # Промпт
    rect_prompt = FancyBboxPatch((6.5, 5.5), 2.2, 1, boxstyle="round,pad=0.1",
                                  edgecolor='#0066cc', facecolor='#e3f2fd', linewidth=1.2)
    ax.add_patch(rect_prompt)
    ax.text(7.6, 6.2, "Промпт", ha='center', fontsize=8, fontweight='bold')
    ax.text(7.6, 5.8, "Контекст +\nПрофиль", ha='center', fontsize=7)
    
    arrow_prompt = FancyArrowPatch((5.9, 3.9), (6.8, 5.5), arrowstyle='->', 
                                  mutation_scale=15, color='#0066cc', linewidth=1.2)
    ax.add_patch(arrow_prompt)
    
    # LLM Qwen2.5
    rect_llm = FancyBboxPatch((6.5, 3.8), 2.2, 1.2, boxstyle="round,pad=0.1",
                               edgecolor='#ff6f00', facecolor='#fff3e0', linewidth=1.5)
    ax.add_patch(rect_llm)
    ax.text(7.6, 4.7, "LLM Qwen2.5", ha='center', fontsize=9, fontweight='bold')
    ax.text(7.6, 4.2, "Генерация\nответа", ha='center', fontsize=7)
    
    arrow_llm = FancyArrowPatch((7.6, 5.5), (7.6, 5.0), arrowstyle='->', 
                               mutation_scale=15, color='#ff6f00', linewidth=1.2)
    ax.add_patch(arrow_llm)
    
    # Проверка верности
    rect_faith = FancyBboxPatch((6.2, 2), 2.8, 1.3, boxstyle="round,pad=0.1",
                                 edgecolor='#c62828', facecolor='#ffebee', linewidth=1.5)
    ax.add_patch(rect_faith)
    ax.text(7.6, 3.0, "Проверка верности", ha='center', fontsize=8, fontweight='bold')
    ax.text(7.6, 2.5, "Порог: 0.35\n(отказ, если ниже)", ha='center', fontsize=7)
    
    arrow_faith = FancyArrowPatch((7.6, 3.8), (7.6, 3.3), arrowstyle='->', 
                                 mutation_scale=15, color='#c62828', linewidth=1.2)
    ax.add_patch(arrow_faith)
    
    # Выход
    rect_out = FancyBboxPatch((5.5, 0.2), 3.5, 0.9, boxstyle="round,pad=0.1",
                               edgecolor='#2e7d32', facecolor='#e8f5e9', linewidth=1.5)
    ax.add_patch(rect_out)
    ax.text(7.25, 0.8, "Ответ + Источники + Уверенность", ha='center', fontsize=8, fontweight='bold')
    
    arrow_out = FancyArrowPatch((7.6, 2.0), (7.25, 1.1), arrowstyle='->', 
                               mutation_scale=20, color='#2e7d32', linewidth=1.5)
    ax.add_patch(arrow_out)
    
    ax.text(0.2, 0.5, "Лексика (BM25): точные слова | Семантика (Dense): значение | Слияние (RRF): комбинирует оба",
            fontsize=7, style='italic', bbox=dict(boxstyle='round', facecolor='#fffacd', alpha=0.3))
    
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "fig_rag_detalle.png"), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print("✓ Рисунок 2 сохранён: fig_rag_detalle.png")

def create_figure_3():
    """Конвейер голоса: вход → обработка → выход"""
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 9)
    ax.axis('off')
    
    ax.text(5.5, 8.6, "Рисунок 3: Конвейер голосового взаимодействия",
            ha='center', fontsize=12, fontweight='bold')
    
    h_input = 7.5
    h_stt = 6.0
    h_process = 4.5
    h_trans = 3.0
    h_tts = 1.5
    
    # Пользователь
    rect_user = FancyBboxPatch((0.2, h_input), 2.2, 0.8, boxstyle="round,pad=0.1",
                                edgecolor='#000', facecolor='#e1f5fe', linewidth=1.5)
    ax.add_patch(rect_user)
    ax.text(1.3, h_input+0.4, "Пользователь", ha='center', fontsize=9, fontweight='bold')
    
    arrow_user = FancyArrowPatch((1.3, h_input), (1.3, h_stt+0.6), arrowstyle='->', 
                                mutation_scale=20, color='#333', linewidth=1.3)
    ax.add_patch(arrow_user)
    
    # STT: Whisper
    rect_whisper = FancyBboxPatch((0.05, h_stt-0.1), 2.5, 1.2, boxstyle="round,pad=0.1",
                                   edgecolor='#ff6f00', facecolor='#fff3e0', linewidth=1.5)
    ax.add_patch(rect_whisper)
    ax.text(1.3, h_stt+0.7, "STT: Whisper", ha='center', fontsize=9, fontweight='bold')
    ax.text(1.3, h_stt+0.2, "Многоязычный\nOllama/OpenAI", ha='center', fontsize=7)
    
    arrow_stt = FancyArrowPatch((1.3, h_stt-0.1), (1.3, h_process+0.6), arrowstyle='->', 
                               mutation_scale=20, color='#ff6f00', linewidth=1.3)
    ax.add_patch(arrow_stt)
    
    # Обработка (RAG + LLM)
    rect_process = FancyBboxPatch((0.05, h_process-0.2), 2.5, 1.3, boxstyle="round,pad=0.1",
                                   edgecolor='#7b1fa2', facecolor='#f3e5f5', linewidth=1.5)
    ax.add_patch(rect_process)
    ax.text(1.3, h_process+0.8, "Обработка", ha='center', fontsize=8, fontweight='bold')
    ax.text(1.3, h_process+0.3, "RAG (Рис. 2)\n+ LLM Qwen2.5", ha='center', fontsize=7)
    
    arrow_process = FancyArrowPatch((1.3, h_process-0.2), (1.3, h_trans+0.5), arrowstyle='->', 
                                   mutation_scale=20, color='#7b1fa2', linewidth=1.3)
    ax.add_patch(arrow_process)
    
    # Перевод
    rect_trans = FancyBboxPatch((0.05, h_trans-0.1), 2.5, 0.9, boxstyle="round,pad=0.1",
                                 edgecolor='#1976d2', facecolor='#e3f2fd', linewidth=1.2)
    ax.add_patch(rect_trans)
    ax.text(1.3, h_trans+0.4, "Перевод", ha='center', fontsize=8, fontweight='bold')
    
    arrow_trans = FancyArrowPatch((1.3, h_trans-0.1), (1.3, h_tts+0.8), arrowstyle='->', 
                                 mutation_scale=20, color='#1976d2', linewidth=1.3)
    ax.add_patch(arrow_trans)
    
    # Web Speech API (Primary)
    rect_tts1 = FancyBboxPatch((3.2, h_tts+0.3), 2.5, 1, boxstyle="round,pad=0.1",
                                edgecolor='#2e7d32', facecolor='#e8f5e9', linewidth=1.5)
    ax.add_patch(rect_tts1)
    ax.text(4.45, h_tts+1.0, "Web Speech API", ha='center', fontsize=8, fontweight='bold')
    ax.text(4.45, h_tts+0.55, "(Основной)", ha='center', fontsize=7)
    
    # gTTS Backend (Fallback)
    rect_tts2 = FancyBboxPatch((3.2, h_tts-0.8), 2.5, 1, boxstyle="round,pad=0.1",
                                edgecolor='#d32f2f', facecolor='#ffebee', linewidth=1.2)
    ax.add_patch(rect_tts2)
    ax.text(4.45, h_tts-0.1, "gTTS Backend", ha='center', fontsize=8)
    ax.text(4.45, h_tts-0.55, "(Резерв)", ha='center', fontsize=7)
    
    arrow_tts1 = FancyArrowPatch((1.3, h_tts+0.8), (3.2, h_tts+0.8), arrowstyle='->', 
                                mutation_scale=15, color='#2e7d32', linewidth=1.3)
    ax.add_patch(arrow_tts1)
    
    arrow_tts2 = FancyArrowPatch((3.7, h_tts+0.3), (3.9, h_tts-0.3), arrowstyle='<->', 
                                mutation_scale=12, color='#d32f2f', linewidth=1.2, linestyle='--')
    ax.add_patch(arrow_tts2)
    
    # Аудио синтез
    rect_audio = FancyBboxPatch((6.5, h_tts-0.3), 2, 1.3, boxstyle="round,pad=0.1",
                                 edgecolor='#ff6f00', facecolor='#fff3e0', linewidth=1.2)
    ax.add_patch(rect_audio)
    ax.text(7.5, h_tts+0.7, "Аудио", ha='center', fontsize=8, fontweight='bold')
    ax.text(7.5, h_tts+0.25, "Синтез речи", ha='center', fontsize=7)
    
    arrow_audio = FancyArrowPatch((5.7, h_tts+0.3), (6.5, h_tts+0.3), arrowstyle='->', 
                                 mutation_scale=15, color='#ff6f00', linewidth=1.2)
    ax.add_patch(arrow_audio)
    
    # Воспроизведение
    rect_out = FancyBboxPatch((6.2, h_tts-1.5), 2.6, 0.9, boxstyle="round,pad=0.1",
                               edgecolor='#2e7d32', facecolor='#e8f5e9', linewidth=1.5)
    ax.add_patch(rect_out)
    ax.text(7.5, h_tts-1.05, "Воспроизведение", ha='center', fontsize=8, fontweight='bold')
    
    arrow_out = FancyArrowPatch((7.5, h_tts-0.3), (7.5, h_tts-0.6), arrowstyle='->', 
                               mutation_scale=20, color='#2e7d32', linewidth=1.3)
    ax.add_patch(arrow_out)
    
    info_text = ("STT: Преобразует аудио в текст через Whisper\n"
                 "Перевод: Определяет язык пользователя, переводит ответ при необходимости\n"
                 "TTS: Web Speech API основной, gTTS автоматический резерв")
    ax.text(0.1, 0.15, info_text, fontsize=7, style='italic', 
            bbox=dict(boxstyle='round', facecolor='#fffacd', alpha=0.3, pad=0.3))
    
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "fig_voz.png"), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print("✓ Рисунок 3 сохранён: fig_voz.png")

if __name__ == '__main__':
    print("=" * 70)
    print("Генерация рисунков 1-3: Профессиональные диаграммы на русском языке")
    print("=" * 70)
    print()
    
    create_figure_1()
    create_figure_2()
    create_figure_3()
    
    print()
    print("=" * 70)
    print("✓ ЗАВЕРШЕНО: 3 рисунка PNG сгенерированы")
    print(f"  {OUT_DIR}")
    print("=" * 70)
