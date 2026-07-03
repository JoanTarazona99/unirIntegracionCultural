"""
Módulo RAG Mejorado - Documentos Oficiales de KubGU
Integración con fuentes oficiales: КубГУ, МВД РФ, МФЦ, Госуслуги

Features:
- Semantic search using sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2)
- LLM integration with Ollama (llama3, qwen2, mistral)
- Keyword fallback if embeddings/LLM fail
- Cosine similarity for semantic matching
- Conversation history per session
"""

import json
import os
import time
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Generator, AsyncGenerator

# Try to import LLM module
LLM_AVAILABLE = False
try:
    from llm_module import get_llm_instance, LLMModule
    LLM_AVAILABLE = True
    print("[RAG] LLM module available - Natural language generation enabled")
except ImportError:
    print("[RAG] LLM module not available - Using template responses")

# Try to import translator for content translation
TRANSLATOR_AVAILABLE = False
try:
    from translator import MultiLanguageTranslator
    _translator_instance = None

    def get_translator():
        global _translator_instance
        if _translator_instance is None:
            _translator_instance = MultiLanguageTranslator()
        return _translator_instance

    TRANSLATOR_AVAILABLE = True
    print("[RAG] Translator available - Content translation enabled")
except ImportError:
    print("[RAG] Translator not available - Content will remain in original language")

    def get_translator():
        return None

# Try to import sentence-transformers for semantic search
# NOTE: Disabled by default due to CPU compatibility issues on some systems.
# Controlled via settings.enable_semantic_search (env: ENABLE_SEMANTIC_SEARCH=1).
SEMANTIC_SEARCH_AVAILABLE = False

# Resolve the flag from centralized settings, falling back to the env var
# so the module still works when imported outside the app context.
try:
    from app.config.settings import settings as _settings
    _semantic_search_enabled = _settings.enable_semantic_search
except Exception:
    _semantic_search_enabled = os.environ.get('ENABLE_SEMANTIC_SEARCH', '0') == '1'

if _semantic_search_enabled:
    try:
        from sentence_transformers import SentenceTransformer
        SEMANTIC_SEARCH_AVAILABLE = True
        print("[RAG] sentence-transformers loaded successfully - Semantic search enabled")
    except ImportError:
        print("[RAG] sentence-transformers not available - Using keyword fallback")
else:
    print("[RAG] Semantic search disabled (keyword fallback active). Set ENABLE_SEMANTIC_SEARCH=1 to enable.")


class SemanticSearchEngine:
    """Motor de búsqueda semántica usando sentence-transformers"""

    def __init__(self, model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2'):
        self.model = None
        self.embeddings = None
        self.documents = []
        self.model_name = model_name
        self._initialized = False

        if SEMANTIC_SEARCH_AVAILABLE:
            try:
                print(f"[RAG] Loading model: {model_name}")
                import warnings
                warnings.filterwarnings('ignore')
                self.model = SentenceTransformer(model_name)
                self._initialized = True
                print("[RAG] Semantic search engine initialized successfully")
            except Exception as e:
                print(f"[RAG] Error loading model: {e}")
                self._initialized = False
            except SystemError as e:
                print(f"[RAG] System error in model loading (likely CPU compatibility): {e}")
                self._initialized = False
            except BaseException as e:
                print(f"[RAG] Unexpected error loading model: {type(e).__name__}: {e}")
                self._initialized = False

    def build_index(self, documents: List[Dict]) -> bool:
        """Build vector index from documents"""
        if not self._initialized or not self.model:
            return False

        try:
            self.documents = []
            texts = []

            for doc in documents:
                # Combine title and content for embedding
                text = f"{doc.get('title', '')} {doc.get('content', '')}"
                texts.append(text)
                self.documents.append(doc)

            print(f"[RAG] Building embeddings for {len(texts)} documents...")
            self.embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            print(f"[RAG] Embeddings built: shape {self.embeddings.shape}")
            return True
        except Exception as e:
            print(f"[RAG] Error building index: {e}")
            return False

    def search(self, query: str, top_k: int = 5) -> List[Tuple[Dict, float]]:
        """Search using cosine similarity"""
        if not self._initialized or self.embeddings is None:
            return []

        try:
            # Encode query
            query_embedding = self.model.encode([query], convert_to_numpy=True, show_progress_bar=False)[0]

            # Compute cosine similarity
            similarities = np.dot(self.embeddings, query_embedding) / (
                np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
            )

            # Get top-k indices
            top_indices = np.argsort(similarities)[::-1][:top_k]

            results = []
            for idx in top_indices:
                if similarities[idx] > 0.3:  # Similarity threshold
                    results.append((self.documents[idx], float(similarities[idx])))

            return results
        except Exception as e:
            print(f"[RAG] Error in semantic search: {e}")
            return []


class OfficialDocumentLibrary:
    """Biblioteca de documentos oficiales para RAG"""

    def __init__(self):
        self.documents = {}
        self.flat_documents = []  # Flattened for embedding
        self.semantic_engine = None
        self._use_semantic = False
        self._initialize_documents()
        self._initialize_semantic_search()

    def _initialize_semantic_search(self):
        """Initialize semantic search if available"""
        if not SEMANTIC_SEARCH_AVAILABLE:
            print("[RAG] Using keyword search mode")
            return

        try:
            print("[RAG] Initializing semantic search engine...")
            self.semantic_engine = SemanticSearchEngine()
            if self.semantic_engine._initialized:
                try:
                    # Flatten documents for embedding
                    self._flatten_documents()
                    # Build the index
                    if self.semantic_engine.build_index(self.flat_documents):
                        self._use_semantic = True
                        print("[RAG] Semantic search mode activated")
                except Exception as e:
                    print(f"[RAG] Error building semantic index: {e}")
                    self._use_semantic = False
            else:
                print("[RAG] Semantic engine not initialized, using keyword fallback")
                self._use_semantic = False
        except Exception as e:
            print(f"[RAG] Error during semantic initialization: {e}")
            self._use_semantic = False
        except BaseException as e:
            print(f"[RAG] Unexpected error during semantic initialization: {type(e).__name__}: {e}")
            self._use_semantic = False

    def _flatten_documents(self):
        """Flatten nested document structure for embedding"""
        self.flat_documents = []
        for source_name, doc in self.documents.items():
            for section in doc.get('sections', []):
                self.flat_documents.append({
                    'source': source_name,
                    'source_url': doc.get('url'),
                    'title': section.get('title'),
                    'content': section.get('content', '').strip()
                })
        print(f"[RAG] Flattened {len(self.flat_documents)} document sections")

    def _initialize_documents(self):
        """Inicializar biblioteca de documentos oficiales"""

        # КубГУ - Información institucional
        self.documents['КубГУ'] = {
            'name': 'Кубанский государственный университет',
            'url': 'https://kubsu.ru',
            'sections': [
                {
                    'title': 'Приём иностранных студентов',
                    'content': '''
                    Кубанский государственный университет приветствует студентов со всего мира.

                    ПРОЦЕДУРА ПРИЁМА:
                    1. Подайте документы через портал вузов (https://cabinet.rt.asurso.ru)
                    2. Получите письмо-приглашение
                    3. Подготовьте документы для визы
                    4. Зарегистрируйтесь в МФЦ или МВД

                    ПОЛЕЗНАЯ ИНФОРМАЦИЯ:
                    - Учебный год: сентябрь - май
                    - Общежитие: доступно для иностранных студентов
                    - Стипендия: возможна для отличников
                    - Медицинское страхование: обязательно
                    '''
                },
                {
                    'title': 'Общежитие и проживание',
                    'content': '''
                    УСЛОВИЯ ПРОЖИВАНИЯ В ОБЩЕЖИТИИ:

                    Комнаты: 2-3 человека на комнату
                    Условия: Кровать, шкаф, письменный стол, стул
                    Коммунальные услуги: Включены в цену
                    Комендантский час: 23:00-6:00 (выходные: 24:00-8:00)

                    СТОИМОСТЬ:
                    - Стандартная комната: ~200-300 рублей/месяц
                    - Общежитие рядом с кампусом: 15 минут в автобусе

                    КОНТАКТ:
                    Администрация общежития: +7-918-XXXXXXX
                    email: dormitory@kubsu.ru
                    '''
                },
                {
                    'title': 'Академическая информация',
                    'content': '''
                    СТРУКТУРА КУРSOS:
                    - Бакалавриат: 4 года
                    - Магистратура: 2 года
                    - Аспирантура: 3 года

                    ЯЗЫК ОБУЧЕНИЯ: Русский
                    ТРЕБОВАНИЯ: ТРКИ B1 для бакалавриата, B2 для магистратуры

                    ЭКЗАМЕНЫ И ОЦЕНКИ:
                    - Экзаменационная сессия: май-июнь
                    - Шкала оценок: 5 (отлично), 4 (хорошо), 3 (удовлетворительно)
                    - Минимальная оценка для прохождения: 3
                    '''
                },
                {
                    'title': 'Расположение и контактная информация КубГУ',
                    'content': '''
                    КУБАНСКИЙ ГОСУДАРСТВЕННЫЙ УНИВЕРСИТЕТ

                    📍 ОСНОВНОЙ КАМПУС:
                    Город: Краснодар
                    Регион: Краснодарский край, Россия
                    Адрес: ул. Ставропольская, 149, Краснодар, 350040
                    Телефон: +7-861-219-91-01
                    Email: info@kubsu.ru
                    Веб-сайт: https://kubsu.ru

                    📍 ФИЛИАЛЫ:
                    - Армавир (Филиал КубГУ в Армавире)
                    - Геленджик (Черноморское побережье)
                    - Сочи (Филиал КубГУ в Сочи)

                    🚀 КАК ДОБРАТЬСЯ:
                    Аэропорт Краснодара: 25 км от основного кампуса
                    Время в пути: 30-40 минут на такси
                    Общественный транспорт: автобусы 1, 15, 23, 43
                    Железнодорожный вокзал: 5 км от кампуса

                    ⏰ ВРЕМЯ РАБОТЫ:
                    - Понедельник-пятница: 08:00-20:00
                    - Суббота: 09:00-15:00
                    - Воскресенье: Закрыто

                    📞 КОНТАКТЫ ДЛЯ ИНОСТРАНЦЕВ:
                    Отдел международного сотрудничества: +7-861-XXX-XXXX
                    Email иностранных студентов: international@kubsu.ru
                    Офис приема: Главное здание, 3 этаж
                    '''
                }
            ]
        }

        # МВД РФ - Информация миграционная
        self.documents['МВД РФ'] = {
            'name': 'Министерство внутренних дел Российской Федерации',
            'url': 'https://мвд.рф',
            'sections': [
                {
                    'title': 'Регистрация по месту пребывания',
                    'content': '''
                    РЕГИСТРАЦИЯ ДЛЯ ИНОСТРАНЦЕВ:

                    СРОКИ: В течение 7 дней после прибытия в Россию

                    ДОКУМЕНТЫ:
                    1. Паспорт
                    2. Визовый листок (виза)
                    3. Миграционная карта (выдана при входе)
                    4. Договор найма или справка о проживании от общежития

                    МЕСТА РЕГИСТРАЦИИ:
                    - Отделение МВД (УФМС)
                    - Многофункциональный центр (МФЦ)

                    СБОРЫ: Обычно бесплатно для студентов
                    СРОКИ ОБРАБОТКИ: 1-3 дня
                    '''
                },
                {
                    'title': 'Типы виз',
                    'content': '''
                    ВИЗА СТУДЕНТА:
                    - Срок действия: 1 год (с возможностью продления)
                    - Причина: Обучение в образовательном учреждении
                    - Назначение: D (долгосрочная виза)

                    ТРЕБОВАНИЯ:
                    - Письмо-приглашение от вуза
                    - Медицинская справка (HIV, туберкулёз)
                    - Финансовые гарантии
                    - Страховка (медицинская или туристическая)

                    ПРОДЛЕНИЕ ВИЗЫ:
                    - Подайте документы за 1 месяц до истечения
                    - Место: МФЦ или УФМС
                    - Время обработки: 5-7 дней
                    '''
                },
                {
                    'title': 'Права и обязанности',
                    'content': '''
                    ПРАВА ИНОСТРАННОГО СТУДЕНТА:
                    - Работа до 20 часов в неделю во время учёбы
                    - Полный рабочий день в период каникул
                    - Соцстраховка при формальной работе

                    ОБЯЗАННОСТИ:
                    - Сохранять регистрацию (актуальность)
                    - Иметь медицинскую страховку
                    - Не нарушать визовый режим
                    - Придерживаться законов РФ
                    '''
                }
            ]
        }

        # МФЦ - Услуги административные
        self.documents['МФЦ'] = {
            'name': 'Многофункциональный центр предоставления государственных услуг',
            'url': 'https://mfc.krasnodar.ru',
            'sections': [
                {
                    'title': 'Регистрация иностранцев',
                    'content': '''
                    УСЛУГА: Постановка иностранного гражданина на миграционный учёт

                    ДОКУМЕНТЫ:
                    - Паспорт (оригинал и копия)
                    - Виза (копия)
                    - Миграционная карта
                    - Справка о месте проживания (от хозяина жилья или вуза)

                    СРОКИ: 3-5 рабочих дней
                    СТОИМОСТЬ: Бесплатно (для студентов)
                    ВРЕМЯ РАБОТЫ: Пн-Пт 8:00-20:00, Сб 8:00-13:00

                    АДРЕС В КРАСНОДАРЕ:
                    ул. Красная, 1
                    Тел: +7-861-XXXXXXX
                    '''
                },
                {
                    'title': 'Полиса ОМС (медицинское страхование)',
                    'content': '''
                    УСЛУГА: Получение полиса обязательного медицинского страхования

                    ДОКУМЕНТЫ:
                    - Паспорт (копия)
                    - СНИЛС (если есть)
                    - Справка о регистрации

                    СРОКИ: 1 день
                    СТОИМОСТЬ: Бесплатно

                    ПОЛЕЗНАЯ ИНФОРМАЦИЯ:
                    - С полисом ОМС получаете доступ ко всем медицинским услугам
                    - Действителен по всей России
                    - Рекомендуется оформить в первую неделю
                    '''
                },
                {
                    'title': 'Справки и свидетельства',
                    'content': '''
                    ДОСТУПНЫЕ СПРАВКИ:
                    - О месте жительства / пребывания
                    - О составе семьи
                    - Справка о судимости (для личного дела)
                    - Выписки из реестра

                    ВРЕМЯ ОБРАБОТКИ: 1-5 рабочих дней
                    СТОИМОСТЬ: Различная (обычно 100-500 руб.)
                    '''
                }
            ]
        }

        # Госуслуги - Электронные услуги
        self.documents['Госуслуги'] = {
            'name': 'Портал государственных услуг Российской Федерации',
            'url': 'https://www.gosuslugi.ru',
            'sections': [
                {
                    'title': 'Регистрация на портале для иностранцев',
                    'content': '''
                    ЛИЧНЫЙ КАБИНЕТ:
                    Иностранные граждане могут зарегистрироваться и получить доступ к услугам

                    УСЛУГИ ДЛЯ ИНОСТРАНЦЕВ:
                    - Запись на приём в органы миграции
                    - Проверка статуса документов
                    - Получение справок в электронном виде

                    ТРЕБОВАНИЯ ДЛЯ РЕГИСТРАЦИИ:
                    - Email или номер телефона
                    - ФИО и дата рождения
                    - Корректная информация о проживании
                    '''
                },
                {
                    'title': 'Электронная запись на приём',
                    'content': '''
                    ЗАПИСЬ К СПЕЦИАЛИСТАМ:
                    - МВД (миграционная служба)
                    - МФЦ (государственные услуги)
                    - Медицинские учреждения

                    ПРЕИМУЩЕСТВА:
                    - Экономия времени в очереди
                    - Указанный день и время
                    - Отсутствие волнений о доступности

                    КАК ЗАПИСАТЬСЯ:
                    1. Войдите на портал Госуслуги
                    2. Найдите нужную услугу
                    3. Нажмите "Записаться"
                    4. Выберите удобное время
                    5. Подтвердите запись
                    '''
                },
                {
                    'title': 'Тип визы Student visa Тип студенческой визы',
                    'content': '''
                    ВИЗА ДЛЯ СТУДЕНТА в Россию:
                    - Срок действия: зависит от программы обучения
                    - Цель: обучение в вузе
                    - Требуется приглашение от вуза
                    - Оформляется в консульстве РФ

                    ДОКУМЕНТЫ:
                    1. Паспорт (действителен мин. 18 месяцев)
                    2. Приглашение от КубГУ
                    3. Анкета визовая
                    4. Фото 3х4 см
                    5. Справка о несудимости
                    '''
                }
            ]
        }

        # FAQs - Часто задаваемые вопросы
        self.documents['FAQ'] = {
            'name': 'Часто Задаваемые Вопросы для иностранных студентов',
            'url': 'https://kubsu.ru/faq',
            'sections': [
                {
                    'title': '¿Dónde está el MFC? Где находится МФЦ?',
                    'content': '''
                    МФЦ находится в центре города Краснодара.

                    Адреса МФЦ в Краснодаре:
                    - Главный офис: ул. Красная, д. 176, корп. 1
                    - Филиал: ул. Кубанская, д. 45
                    - Филиал: пр. Карла Маркса, д. 77

                    Время работы: ПН-ПТ 08:00-19:00, СБ 09:00-13:00
                    Телефон: +7-861-262-0000
                    '''
                },
                {
                    'title': '¿Cómo me registro? Как пройти регистрацию?',
                    'content': '''
                    ПРОЦЕСС РЕГИСТРАЦИИ:
                    1. Приход в МФЦ с документами
                    2. Получение номера в электроную очередь
                    3. Ожидание вызова оператора
                    4. Подача документов оператору
                    5. Получение расписки
                    6. Ожидание результата (обычно 3-5 дней)

                    ВАЖНО: Не откладывайте регистрацию!
                    Штраф за опоздание: 5000-7000 рублей
                    '''
                },
                {
                    'title': '¿Información sobre dormitorio? Информация о общежитии',
                    'content': '''
                    ОБЩЕЖИТИЕ ДЛЯ ИНОСТРАННЫХ СТУДЕНТОВ:

                    УСЛОВИЯ:
                    - 2-3 человека на комнату
                    - Кровать, шкаф, письменный стол
                    - Общие кухня и ванная
                    - Интернет включен

                    СТОИМОСТЬ: 150-300 рублей в месяц
                    ЗАЯВКА: Отправить эл. письмо на dormitory@kubsu.ru

                    КОМЕНДАНТСКИЙ ЧАС:
                    - Будни: 23:00-07:00
                    - Выходные: 24:00-08:00
                    '''
                },
                {
                    'title': '¿Cómo conseguir póliza médica? Как получить медицинский полис?',
                    'content': '''
                    МЕДИЦИНСКОЕ СТРАХОВАНИЕ ОБЯЗАТЕЛЬНО:

                    ПРОЦЕСС:
                    1. Обратитесь в страховую компанию МФЦ
                    2. Предоставьте документы
                    3. Оплатите полис (5000-8000 руб/год)
                    4. Получите полис ОМС

                    ПОЛИС ДЕЙСТВИТЕЛЕН:
                    - В любой государственной клинике
                    - В частных учреждениях по договору
                    - Включает: консультации, анализы, лечение
                    '''
                },
                {
                    'title': '¿Qué nivel de ruso necesito? Какой уровень русского языка нужен?',
                    'content': '''
                    ТРЕБОВАНИЯ ПО РУССКОМУ ЯЗЫКУ:

                    БАКАЛАВРИАТ:
                    - Минимум: уровень B1 (сертификат ТРКИ-II)
                    - Рекомендуется: B2 для полноценного обучения

                    МАГИСТРАТУРА:
                    - Минимум: B2

                    ПОДГОТОВИТЕЛЬНЫЙ КУРС:
                    - Доступен при КубГУ
                    - Интенсив: 3-6 месяцев
                    - Стоимость: 50000-100000 руб
                    '''
                }
            ]
        }

        # ГУВМ МВД - Migración detallada (bilingüe RU/ES)
        self.documents['ГУВМ МВД'] = {
            'name': 'Главное управление по вопросам миграции МВД России',
            'url': 'https://мвд.рф/mvd/structure1/Glavnie_upravlenija/guvm',
            'sections': [
                {
                    'title': 'Миграционная карта / Tarjeta de migración',
                    'content': '''
                    МИГРАЦИОННАЯ КАРТА / TARJETA DE MIGRACIÓN

                    La tarjeta de migración (миграционная карта) se entrega gratis al cruzar
                    la frontera de Rusia. Es un documento obligatorio.

                    IMPORTANTE / ВАЖНО:
                    - Consérvala hasta salir del país / Храните до выезда
                    - Indica el motivo de entrada: "учёба" (estudios) / Цель въезда: учёба
                    - Si la pierdes, acude al ГУВМ МВД en 3 días / При потере обратитесь в течение 3 дней
                    - Es necesaria para el registro migratorio / Нужна для миграционного учёта

                    Multa por pérdida / Штраф за утерю: 2000-5000 руб.
                    '''
                },
                {
                    'title': 'Продление визы / Prórroga de la visa de estudiante',
                    'content': '''
                    PRÓRROGA DE LA VISA / ПРОДЛЕНИЕ ВИЗЫ

                    La visa de estudiante se prorroga cada año a través de la universidad.

                    PROCESO / ПРОЦЕСС:
                    1. La oficina internacional de KubGU prepara los documentos / Международный отдел готовит документы
                    2. Presenta la solicitud 20 días antes del vencimiento / Подать заявление за 20 дней до окончания
                    3. Paga la tasa estatal / Оплатить госпошлину: 1600 руб.
                    4. Espera la resolución del ГУВМ МВД / Ожидать решение: 20 дней

                    DOCUMENTOS / ДОКУМЕНТЫ:
                    - Pasaporte y visa / Паспорт и виза
                    - Carta de la universidad / Ходатайство вуза
                    - Tarjeta de migración / Миграционная карта
                    - Registro vigente / Действующая регистрация
                    '''
                },
                {
                    'title': 'Патент и разрешение на работу / Permiso de trabajo',
                    'content': '''
                    TRABAJO PARA ESTUDIANTES EXTRANJEROS / РАБОТА ДЛЯ ИНОСТРАННЫХ СТУДЕНТОВ

                    Los estudiantes de tiempo completo pueden trabajar SIN patente ni permiso
                    especial si trabajan en su universidad o durante las vacaciones.
                    Студенты-очники могут работать без патента в своём вузе или на каникулах.

                    REGLAS / ПРАВИЛА:
                    - Trabajo compatible con estudios / Работа совместимая с учёбой
                    - Contrato laboral oficial / Официальный трудовой договор
                    - Necesitas ИНН y СНИЛС / Нужны ИНН и СНИЛС
                    - Al terminar/abandonar estudios el permiso se cancela / При отчислении разрешение аннулируется
                    '''
                }
            ]
        }

        # Здравоохранение - Salud y sanidad
        self.documents['Здравоохранение'] = {
            'name': 'Система здравоохранения России / Sistema de salud',
            'url': 'https://www.rospotrebnadzor.ru',
            'sections': [
                {
                    'title': 'Медицинский осмотр / Examen médico obligatorio',
                    'content': '''
                    EXAMEN MÉDICO OBLIGATORIO / ОБЯЗАТЕЛЬНЫЙ МЕДОСМОТР

                    Los estudiantes extranjeros deben pasar un examen médico en los primeros
                    90 días. Иностранные студенты проходят медосмотр в первые 90 дней.

                    PRUEBAS / ОБСЛЕДОВАНИЯ:
                    - VIH / ВИЧ
                    - Tuberculosis (fluorografía) / Туберкулёз (флюорография)
                    - Lepra y otras enfermedades infecciosas / Проказа и инфекции
                    - Adicción a drogas / Наркозависимость

                    DÓNDE / ГДЕ: Centro médico autorizado / Уполномоченный медцентр
                    COSTO / СТОИМОСТЬ: 5000-9000 руб.
                    RESULTADO / РЕЗУЛЬТАТ: Certificado médico / Медицинское заключение
                    '''
                },
                {
                    'title': 'Поликлиника и врач / Policlínica y médico',
                    'content': '''
                    ATENCIÓN MÉDICA / МЕДИЦИНСКАЯ ПОМОЩЬ

                    Con el seguro médico (ОМС/ДМС) puedes acudir a la policlínica.
                    С полисом можно обращаться в поликлинику.

                    CÓMO / КАК:
                    1. Regístrate en la policlínica del distrito / Прикрепиться к поликлинике
                    2. Pide cita con el terapeuta / Записаться к терапевту
                    3. Lleva pasaporte y póliza / Взять паспорт и полис

                    URGENCIAS / СКОРАЯ ПОМОЩЬ: llama al 103 o 112 (gratis) / звоните 103 или 112
                    Farmacia / Аптека: аптека - medicamentos con o sin receta
                    '''
                }
            ]
        }

        # Банк - Servicios bancarios
        self.documents['Банк'] = {
            'name': 'Банковские услуги для студентов / Servicios bancarios',
            'url': 'https://www.sberbank.ru',
            'sections': [
                {
                    'title': 'Открытие счёта / Abrir una cuenta bancaria',
                    'content': '''
                    ABRIR UNA CUENTA BANCARIA / ОТКРЫТИЕ БАНКОВСКОГО СЧЁТА

                    Los estudiantes extranjeros pueden abrir cuenta y tarjeta en bancos rusos
                    (Сбербанк, Тинькофф, ВТБ, Альфа-Банк).

                    DOCUMENTOS / ДОКУМЕНТЫ:
                    - Pasaporte con traducción notarial / Паспорт с нотариальным переводом
                    - Visa y tarjeta de migración / Виза и миграционная карта
                    - Registro migratorio / Миграционная регистрация
                    - ИНН (número de contribuyente) / ИНН
                    - Certificado de estudios de KubGU / Справка из КубГУ

                    TARJETA / КАРТА: Мир (sistema nacional) recomendada para estudiantes.
                    Las tarjetas Visa/Mastercard extranjeras pueden no funcionar en Rusia.
                    Иностранные Visa/Mastercard могут не работать в России.
                    '''
                },
                {
                    'title': 'Оплата и переводы / Pagos y transferencias',
                    'content': '''
                    PAGOS Y TRANSFERENCIAS / ПЛАТЕЖИ И ПЕРЕВОДЫ

                    - Pago por SBP (Система быстрых платежей) con número de teléfono / Оплата по СБП
                    - Aplicación móvil del banco / Мобильное приложение банка
                    - Pago de la residencia y matrícula / Оплата общежития и обучения
                    - Transferencias entre tarjetas Мир / Переводы между картами Мир

                    CONSEJO / СОВЕТ: activa las notificaciones SMS / Подключите SMS-уведомления
                    '''
                }
            ]
        }

        # Документы - SNILS, INN, otros
        self.documents['Документы РФ'] = {
            'name': 'Личные документы в России / Documentos personales',
            'url': 'https://www.nalog.gov.ru',
            'sections': [
                {
                    'title': 'ИНН - número de contribuyente',
                    'content': '''
                    ИНН / NÚMERO DE IDENTIFICACIÓN FISCAL

                    El ИНН (ИНН - идентификационный номер налогоплательщика) es necesario
                    para trabajar y para operaciones bancarias.

                    DÓNDE / ГДЕ: Servicio Fiscal (ФНС) o МФЦ / Налоговая или МФЦ
                    DOCUMENTOS / ДОКУМЕНТЫ: pasaporte + traducción, registro / Паспорт + перевод, регистрация
                    COSTO / СТОИМОСТЬ: gratis / бесплатно
                    PLAZO / СРОК: 5 días hábiles / 5 рабочих дней
                    '''
                },
                {
                    'title': 'СНИЛС - seguro social',
                    'content': '''
                    СНИЛС / NÚMERO DE SEGURO SOCIAL

                    El СНИЛС es el número de la cuenta individual del seguro de pensiones.
                    Necesario para trabajar oficialmente y recibir servicios.

                    DÓNDE / ГДЕ: Фонд пенсионного и социального страхования (СФР) o МФЦ
                    DOCUMENTOS / ДОКУМЕНТЫ: pasaporte + traducción / Паспорт + перевод
                    COSTO / СТОИМОСТЬ: gratis / бесплатно
                    PLAZO / СРОК: 1-5 días / 1-5 дней
                    '''
                }
            ]
        }

        # Транспорт Краснодара - Transporte
        self.documents['Транспорт'] = {
            'name': 'Общественный транспорт Краснодара / Transporte de Krasnodar',
            'url': 'https://transport.krd.ru',
            'sections': [
                {
                    'title': 'Городской транспорт / Transporte urbano',
                    'content': '''
                    TRANSPORTE EN KRASNODAR / ТРАНСПОРТ В КРАСНОДАРЕ

                    TIPOS / ВИДЫ:
                    - Tranvía / Трамвай
                    - Trolebús / Троллейбус
                    - Autobús / Автобус
                    - Marshrutka (minibús) / Маршрутка

                    PAGO / ОПЛАТА:
                    - Tarjeta de transporte "Транспортная карта" / Транспортная карта
                    - Tarjeta bancaria Мир sin contacto / Бесконтактная карта Мир
                    - Efectivo al conductor / Наличные водителю
                    Tarifa aproximada / Стоимость проезда: 35-40 руб.

                    Cómo llegar a KubGU / Как добраться до КубГУ:
                    autobuses / автобусы 1, 15, 23, 43 hasta "ул. Ставропольская".
                    '''
                },
                {
                    'title': 'Такси и каршеринг / Taxi y coche compartido',
                    'content': '''
                    TAXI Y APLICACIONES / ТАКСИ И ПРИЛОЖЕНИЯ

                    - Яндекс Go (Yandex Go) - la más popular / самая популярная
                    - Максим (Maxim)
                    - Ситимобил

                    CONSEJO / СОВЕТ: pide taxi por la aplicación, es más barato y seguro
                    que en la calle. Заказывайте такси через приложение - дешевле и безопаснее.

                    Tren / Поезд: estación Краснодар-1 para viajes a otras ciudades (РЖД).
                    '''
                }
            ]
        }

        # Мобильная связь - SIM y comunicaciones
        self.documents['Мобильная связь'] = {
            'name': 'Мобильная связь и интернет / Telefonía móvil',
            'url': 'https://www.gosuslugi.ru',
            'sections': [
                {
                    'title': 'SIM-карта / Comprar una tarjeta SIM',
                    'content': '''
                    TARJETA SIM RUSA / РОССИЙСКАЯ SIM-КАРТА

                    Operadores / Операторы: МТС, Билайн, МегаФон, Tele2, Yota.

                    PARA COMPRAR / ДЛЯ ПОКУПКИ:
                    - Pasaporte con traducción / Паспорт с переводом
                    - Tarjeta de migración / Миграционная карта
                    - A veces registro / Иногда регистрация

                    IMPORTANTE / ВАЖНО:
                    - Registra la SIM a tu nombre / Оформляйте SIM на своё имя
                    - No compres SIM en la calle sin registro / Не покупайте SIM без оформления
                    - Necesaria para bancos y Госуслуги / Нужна для банков и Госуслуг
                    Costo / Стоимость: 300-700 руб. con saldo.
                    '''
                }
            ]
        }

        # Безопасность - Emergencias y seguridad
        self.documents['Безопасность'] = {
            'name': 'Экстренные службы и безопасность / Emergencias',
            'url': 'https://мчс.рф',
            'sections': [
                {
                    'title': 'Телефоны экстренных служб / Números de emergencia',
                    'content': '''
                    NÚMEROS DE EMERGENCIA / ЭКСТРЕННЫЕ ТЕЛЕФОНЫ

                    - 112 - Emergencia general (todos los servicios) / Единый номer
                    - 101 - Bomberos / Пожарная служба
                    - 102 - Policía / Полиция
                    - 103 - Ambulancia / Скорая помощь
                    - 104 - Fuga de gas / Аварийная газовая служба

                    El 112 funciona sin saldo y sin SIM / 112 работает без денег и без SIM.
                    Puedes hablar en inglés en el 112 en muchas regiones.

                    CONSEJO / СОВЕТ: guarda estos números y la dirección de tu residencia
                    en ruso. Сохраните адрес общежития на русском языке.
                    '''
                },
                {
                    'title': 'Потеря документов / Pérdida de documentos',
                    'content': '''
                    PÉRDIDA DE DOCUMENTOS / УТЕРЯ ДОКУМЕНТОВ

                    Si pierdes el pasaporte / При утере паспорта:
                    1. Denuncia en la policía (102) / Заявить в полицию
                    2. Contacta tu consulado / Обратиться в консульство
                    3. Informa a la oficina internacional de KubGU / Сообщить в международный отдел

                    Si pierdes visa/tarjeta de migración / При утере визы или миграционной карты:
                    acude al ГУВМ МВД en 3 días / обратитесь в ГУВМ МВД в течение 3 дней.
                    '''
                }
            ]
        }

        # Стипендии - Becas y finanzas
        self.documents['Стипендии'] = {
            'name': 'Стипендии и финансовая поддержка / Becas',
            'url': 'https://kubsu.ru',
            'sections': [
                {
                    'title': 'Виды стипендий / Tipos de becas',
                    'content': '''
                    BECAS PARA ESTUDIANTES / СТИПЕНДИИ ДЛЯ СТУДЕНТОВ

                    - Beca del gobierno ruso (cuota estatal) / Стипендия по квоте Правительства РФ
                    - Beca académica por buenas notas / Академическая стипендия за успеваемость
                    - Beca social / Социальная стипендия

                    CUOTA ESTATAL / ГОСУДАРСТВЕННАЯ КВОТА (Rossotrudnichestvo):
                    - Matrícula gratuita / Бесплатное обучение
                    - Beca mensual / Ежемесячная стипендия
                    - Plaza en residencia / Место в общежитии
                    Solicitud / Заявка: education-in-russia.com (Отбор)
                    '''
                }
            ]
        }

        # Адаптация - Adaptación cultural
        self.documents['Адаптация'] = {
            'name': 'Культурная адаптация / Adaptación cultural',
            'url': 'https://kubsu.ru',
            'sections': [
                {
                    'title': 'Советы по адаптации / Consejos de adaptación',
                    'content': '''
                    ADAPTACIÓN CULTURAL / КУЛЬТУРНАЯ АДАПТАЦИЯ

                    - Aprende ruso básico cuanto antes / Учите базовый русский как можно раньше
                    - El clima de Krasnodar es templado, inviernos suaves / Климат Краснодара мягкий
                    - Horario de tiendas: normalmente 9:00-21:00 / Магазины работают 9:00-21:00
                    - Supermercados: Магнит, Пятёрочка, Лента / Супермаркеты
                    - Usa Яндекс Карты y 2ГИС para orientarte / Используйте Яндекс Карты и 2ГИС

                    ASOCIACIÓN DE ESTUDIANTES EXTRANJEROS / АССОЦИАЦИЯ ИНОСТРАННЫХ СТУДЕНТОВ:
                    KubGU tiene un club internacional que organiza eventos y apoyo.
                    В КубГУ есть международный клуб - мероприятия и поддержка.
                    Contacto / Контакт: international@kubsu.ru
                    '''
                },
                {
                    'title': 'Праздники и традиции / Fiestas y tradiciones',
                    'content': '''
                    FIESTAS PRINCIPALES / ОСНОВНЫЕ ПРАЗДНИКИ

                    - Año Nuevo (31 dic - 8 ene) - la fiesta más importante / Новый год
                    - Día del Defensor de la Patria (23 feb) / День защитника Отечества
                    - Día Internacional de la Mujer (8 mar) / Международный женский день
                    - Día de la Victoria (9 may) / День Победы
                    - Día de Rusia (12 jun) / День России

                    En estos días muchas oficinas cierran / В праздники учреждения не работают.
                    Planifica trámites con antelación / Планируйте документы заранее.
                    '''
                }
            ]
        }

        # Языковая подготовка - TRKI / idioma ruso
        self.documents['Русский язык'] = {
            'name': 'Русский язык и ТРКИ / Idioma ruso y certificación',
            'url': 'https://kubsu.ru',
            'sections': [
                {
                    'title': 'Сертификат ТРКИ / Certificado TRKI',
                    'content': '''
                    CERTIFICADO TRKI / СЕРТИФИКАТ ТРКИ

                    El ТРКИ (Тест по русскому языку как иностранному) certifica tu nivel
                    de ruso, equivalente al MCER.

                    NIVELES / УРОВНИ:
                    - ТРКИ-I = B1 (mínimo para grado / минимум для бакалавриата)
                    - ТРКИ-II = B2 (máster / магистратура)
                    - ТРКИ-III = C1

                    Preparación / Подготовка: curso preparatorio de KubGU (3-6 meses).
                    Подготовительный факультет КубГУ.
                    Costo del examen / Стоимость экзамена: aproximadamente 3000-6000 руб.
                    '''
                }
            ]
        }

        # Жильё - Vivienda (alquiler privado)
        self.documents['Жильё'] = {
            'name': 'Аренда жилья / Alquiler de vivienda',
            'url': 'https://kubsu.ru',
            'sections': [
                {
                    'title': 'Аренда квартиры / Alquilar un apartamento',
                    'content': '''
                    ALQUILER PRIVADO / АРЕНДА КВАРТИРЫ

                    Si no vives en la residencia, puedes alquilar un apartamento.
                    Если не живёте в общежитии, можно снять квартиру.

                    PLATAFORMAS / ПЛОЩАДКИ: Авито, Циан, Домклик.

                    IMPORTANTE / ВАЖНО:
                    - Firma un contrato de alquiler / Заключите договор аренды
                    - El propietario debe registrarte (миграционный учёт) / Собственник обязан оформить регистрацию
                    - Sin registro tendrás problemas legales / Без регистрации - проблемы с законом
                    - Precio en Krasnodar / Цена в Краснодаре: 15000-30000 руб./mes por 1 habitación

                    CONSEJO / СОВЕТ: desconfía de precios muy bajos / Остерегайтесь слишком низких цен.
                    '''
                }
            ]
        }

        # Питание - Comida y comedores
        self.documents['Питание'] = {
            'name': 'Питание для студентов / Alimentación',
            'url': 'https://kubsu.ru',
            'sections': [
                {
                    'title': 'Столовая и кафе / Comedor y cafeterías',
                    'content': '''
                    ALIMENTACIÓN / ПИТАНИЕ

                    - Comedor universitario (столовая) - económico / Университетская столовая - недорого
                    - Menú del día 150-250 руб. / Комплексный обед 150-250 руб.
                    - Cafeterías en el campus / Кафе на кампусе

                    COMPRAS / ПОКУПКИ:
                    - Supermercados: Магнит, Пятёрочка, Лента, Ашан
                    - Mercados locales de frutas y verduras / Рынки: фрукты и овощи

                    COMIDA HALAL / ХАЛЯЛЬ: hay tiendas y cafés halal en Krasnodar.
                    В Краснодаре есть халяльные магазины и кафе.
                    '''
                }
            ]
        }

    def search(self, query: str, source: Optional[str] = None) -> List[Dict]:
        """Search in documents - semantic or keyword based on availability"""

        # Try semantic search first
        if self._use_semantic and self.semantic_engine:
            semantic_results = self.semantic_engine.search(query, top_k=5)
            if semantic_results:
                results = []
                for doc, similarity in semantic_results:
                    results.append({
                        'source': doc['source'],
                        'source_url': doc['source_url'],
                        'title': doc['title'],
                        'content': doc['content'],
                        'relevance': similarity,
                        'search_mode': 'semantic'
                    })
                return results

        # Fallback to keyword search
        return self._keyword_search(query, source)

    def _keyword_search(self, query: str, source: Optional[str] = None) -> List[Dict]:
        """Fallback keyword-based search with synonym expansion"""
        results = []
        query_lower = query.lower()
        query_words = set(query_lower.split())

        # Keyword mapping (Spanish/Russian synonyms)
        keyword_mapping = {
            'registro': ['регистрация', 'registro'],
            'mfc': ['мфц', 'mfc'],
            'migracion': ['миграция', 'миграционная', 'миграционной', 'migracion'],
            'visa': ['виза', 'visa'],
            'dormitorio': ['общежитие', 'dormitorio'],
            'vivienda': ['проживание', 'жилье', 'vivienda'],
            'profesor': ['преподаватель', 'profesor'],
            'clase': ['урок', 'занятие', 'clase'],
            'examen': ['экзамен', 'examen'],
            'poliza': ['полис', 'страхование', 'poliza'],
            'medico': ['медицинский', 'врач', 'medico'],
            'pasaporte': ['паспорт', 'pasaporte'],
            'documento': ['документ', 'documento'],
            'estudiante': ['студент', 'estudiante'],
            'rusol': ['русский', 'язык', 'русском'],
            'donde': ['направление', 'адрес', 'локация', 'местоположение', 'расположение', 'ubicacion', 'location', 'where', 'краснодар', 'krasnodar'],
            'como': ['как', 'процесс', 'procedimiento', 'como'],
            'informacion': ['информация', 'info', 'informacion'],
            'gastos': ['стоимость', 'цена', 'gastos'],
            'costo': ['стоимость', 'руб', 'costo'],
            'ubicacion': ['адрес', 'местоположение', 'расположение', 'краснодар', 'krasnodar', 'ubicacion'],
            'localización': ['адрес', 'местоположение', 'расположение', 'локация', 'localizacion'],
            'direcion': ['адрес', 'направление', 'calle', 'улица', 'direccion'],
            'address': ['адрес', 'направление', 'address', 'местоположение'],
            'location': ['местоположение', 'расположение', 'адрес', 'location'],
            'campus': ['кампус', 'campus', 'здание', 'здания'],
            'ciudad': ['город', 'краснодар', 'ciudad'],
            'city': ['город', 'краснодар', 'city'],
            'telefono': ['телефон', 'контакт', 'телефонный', 'telefono'],
            'contacto': ['контакт', 'телефон', 'email', 'contacto'],
            'contact': ['контакт', 'телефон', 'email', 'contact'],
            'kubgu': ['кубгу', 'кубанский', 'университет', 'kubgu'],
            'university': ['университет', 'вуз', 'university', 'кубгу'],
            'транспорт': ['транспорт', 'автобус', 'метро', 'такси', 'transport', 'добраться'],
            'como_llegar': ['как', 'добраться', 'маршрут', 'транспорт', 'llegada']
        }

        # Expand query words with synonyms
        expanded_words = set(query_words)
        for keyword, synonyms in keyword_mapping.items():
            if keyword in query_words:
                expanded_words.update(synonyms)

        # Detect if query is about KubGU location
        query_normalized = query_lower.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
        is_kubgu_location_query = ('кубгу' in query_lower or 'kubgu' in query_normalized or 'kuban' in query_normalized or 'universidad' in query_normalized) and \
                                 any(word in query_normalized for word in ['donde', 'dónde', 'где', 'ubicacion', 'localizacion', 'ciudad', 'city', 'location', 'raspolozhen', 'adres', 'dirección', 'direccion'])

        # Search in all documents
        for source_name in self.documents.keys():
            doc = self.documents[source_name]

            for section in doc.get('sections', []):
                title = section.get('title', '').lower()
                content = section.get('content', '').lower()

                # Calculate relevance score
                match_score = 0

                # PRIORITY BOOST: If query is about КубГУ location and section is about location/contacts
                if is_kubgu_location_query and source_name == 'КубГУ' and ('расположение' in title or 'контактная' in title or 'адрес' in title):
                    match_score = 1.0  # Maximum priority for КубГУ location sections
                elif query_lower in title:
                    match_score = 1.0
                elif query_lower in content:
                    match_score = 0.8
                else:
                    # Word matching
                    matched_words = 0
                    for word in expanded_words:
                        if len(word) > 2:
                            if word in title:
                                matched_words += 3
                            elif word in content:
                                matched_words += 1

                    if matched_words > 0:
                        match_score = min(0.9, matched_words * 0.1)

                # Boost score for КубГУ location sections when searching for КубГУ info
                if source_name == 'КубГУ' and ('расположение' in title or 'контактная' in title) and match_score > 0:
                    match_score = min(1.0, match_score * 1.3)

                if match_score > 0.3:
                    results.append({
                        'source': source_name,
                        'source_url': doc.get('url'),
                        'title': section.get('title'),
                        'content': section.get('content').strip(),
                        'relevance': match_score,
                        'search_mode': 'keyword'
                    })

        # Sort by relevance
        results.sort(key=lambda x: x['relevance'], reverse=True)

        # Return top results or fallback info
        if not results:
            results.append({
                'source': 'KubGU',
                'source_url': 'https://kubsu.ru',
                'title': 'Informacion General',
                'content': f'Para mas informacion sobre "{query}", visite https://kubsu.ru o contacte a la administracion',
                'relevance': 0.3,
                'search_mode': 'fallback'
            })

        return results

    def get_source(self, source_name: str) -> Optional[Dict]:
        """Get information from a specific source"""
        return self.documents.get(source_name)

    def list_sources(self) -> List[str]:
        """List all available sources"""
        return list(self.documents.keys())

    def get_all_sections(self, source: str) -> List[Dict]:
        """Get all sections from a source"""
        if source in self.documents:
            return self.documents[source].get('sections', [])
        return []

    def get_search_mode(self) -> str:
        """Return current search mode"""
        return "semantic" if self._use_semantic else "keyword"


class EnhancedRAGModule:
    """Módulo RAG mejorado con documentos reales, búsqueda semántica y LLM"""

    def __init__(self, use_llm: bool = True):
        self.document_library = OfficialDocumentLibrary()
        self.cache = {}
        self.llm = None
        self._use_llm = use_llm
        # Advanced retrieval (bm25/dense/hybrid) is built lazily and only used
        # when settings.retrieval_mode != 'keyword'. Defaults keep legacy behaviour.
        self._retriever = None
        self._retrieval_config = self._load_retrieval_config()

        # Initialize LLM if available
        if use_llm and LLM_AVAILABLE:
            try:
                self.llm = get_llm_instance()
                if self.llm.is_available():
                    print("[RAG] LLM integration activated - Natural responses enabled")
                else:
                    print("[RAG] LLM not available - Template responses active")
            except Exception as e:
                print(f"[RAG] LLM initialization failed: {e}")
                self.llm = None

    def _load_retrieval_config(self) -> Dict:
        """Resolve retrieval/trust settings, tolerant of missing app context."""
        config = {
            "mode": "keyword",
            "dense_model": "paraphrase-multilingual-MiniLM-L12-v2",
            "reranker_model": "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
            "rrf_k": 60,
            "top_k": 5,
            "citation_guard": False,
            "abstention_threshold": 0.35,
        }
        try:
            from app.config.settings import settings as _settings
            config["mode"] = getattr(_settings, "retrieval_mode", "keyword")
            config["dense_model"] = getattr(_settings, "dense_model", config["dense_model"])
            config["reranker_model"] = getattr(_settings, "reranker_model", config["reranker_model"])
            config["rrf_k"] = getattr(_settings, "rrf_k", 60)
            config["top_k"] = getattr(_settings, "retrieval_top_k", 5)
            config["citation_guard"] = getattr(_settings, "enable_citation_guard", False)
            config["abstention_threshold"] = getattr(_settings, "abstention_threshold", 0.35)
        except Exception:
            config["mode"] = os.environ.get("RETRIEVAL_MODE", "keyword")
        return config

    def _get_retriever(self):
        """Lazily build the advanced retriever for the configured mode."""
        if self._retriever is not None:
            return self._retriever
        try:
            from retrieval import build_chunks_from_library, build_retriever
            chunks = build_chunks_from_library(self.document_library)
            self._retriever = build_retriever(
                self._retrieval_config["mode"],
                chunks,
                library=self.document_library,
                dense_model=self._retrieval_config["dense_model"],
                reranker_model=self._retrieval_config["reranker_model"],
                rrf_k=self._retrieval_config["rrf_k"],
            )
        except Exception as e:
            print(f"[RAG] Advanced retriever unavailable, using keyword search: {e}")
            self._retriever = None
        return self._retriever

    def _retrieve(self, query: str) -> Tuple[List[Dict], str]:
        """
        Retrieve results using the configured strategy.

        Returns (results, search_mode). Falls back to the legacy keyword search
        when retrieval_mode is 'keyword' or the advanced retriever is unavailable.
        """
        mode = self._retrieval_config.get("mode", "keyword")
        if mode and mode != "keyword":
            retriever = self._get_retriever()
            if retriever is not None:
                try:
                    hits = retriever.search(query, top_k=self._retrieval_config["top_k"])
                    if hits:
                        results = [h.chunk.to_result_dict(h.score, mode) for h in hits]
                        return results, mode
                except Exception as e:
                    print(f"[RAG] Advanced retrieval failed ({mode}): {e}")
        # Legacy path.
        return self.document_library.search(query), self.document_library.get_search_mode()

    def is_llm_enabled(self) -> bool:
        """Check if LLM is currently enabled"""
        return self.llm is not None and self.llm.is_available()

    def search_and_generate(
        self,
        query: str,
        context_type: str = "general",
        language: str = "ru",
        session_id: str = None,
        use_llm: bool = True
    ) -> Dict:
        """
        Search documents and generate contextualized response

        Uses LLM if available for natural language generation,
        otherwise falls back to template responses.

        Args:
            query: User query
            context_type: Type of context (general, chat, profile_*)
            language: Response language (ru, es, en)
            session_id: Optional session ID for conversation history
            use_llm: Whether to use LLM (default True)

        Returns:
            Dict with response, sources, and metadata
        """

        # Search in document library (keyword baseline or advanced retrieval)
        _t_retrieval_start = time.perf_counter()
        results, search_mode = self._retrieve(query)
        retrieval_ms = (time.perf_counter() - _t_retrieval_start) * 1000.0

        # Determine response mode
        response_mode = "template"
        response = None
        llm_ms = 0.0
        llm_stats = {}

        # Try LLM first if available and enabled
        if use_llm and self.is_llm_enabled():
            try:
                _t_llm_start = time.perf_counter()
                response = self.llm.generate_response(
                    query=query,
                    context_docs=results,
                    language=language,
                    session_id=session_id
                )
                llm_ms = (time.perf_counter() - _t_llm_start) * 1000.0
                llm_stats = dict(getattr(self.llm, "last_generation_stats", {}) or {})
                response_mode = "llm"
            except Exception as e:
                print(f"[RAG] LLM generation failed: {e}")
                response = None

        # Fallback to template response
        if response is None:
            response = self._generate_template_response(query, results, language)
            response_mode = "template"

        # Trustworthy-AI guard: verify grounding and abstain if unsupported.
        grounding = None
        if self._retrieval_config.get("citation_guard") and results:
            try:
                from trust import enforce_grounding
                grounding = enforce_grounding(
                    response,
                    results,
                    threshold=self._retrieval_config.get("abstention_threshold", 0.35),
                    language=language,
                )
                response = grounding.answer
                if grounding.abstained:
                    response_mode = "abstained"
            except Exception as e:
                print(f"[RAG] Grounding guard failed: {e}")

        payload = {
            'query': query,
            'response': response,
            'sources_found': len(results),
            'sources': results[:3],
            'context_type': context_type,
            'search_mode': search_mode,
            'response_mode': response_mode,
            'language': language,
            'session_id': session_id
        }
        if grounding is not None:
            payload['grounding'] = {
                'grounded': grounding.grounded,
                'score': round(grounding.score, 3),
                'abstained': grounding.abstained,
                'citations': grounding.citations,
            }

        # ===== AI transparency metrics (non-destructive, informational) =====
        # Per-source retrieval scores.
        retrieval_scores = [
            {
                'source': r.get('source', 'Unknown'),
                'title': r.get('title', ''),
                'score': round(float(r.get('relevance', 0.0)), 3),
            }
            for r in results[:5]
        ]

        # Lexical faithfulness estimate against retrieved content (no abstention).
        faithfulness = None
        if grounding is not None:
            faithfulness = round(grounding.score, 3)
        else:
            try:
                from trust import estimate_faithfulness
                contexts = [r.get('content', '') for r in results]
                if contexts:
                    faithfulness = round(estimate_faithfulness(response, contexts), 3)
            except Exception as e:
                print(f"[RAG] Faithfulness estimate failed: {e}")

        payload['ai_metrics'] = {
            'search_mode': search_mode,
            'response_mode': response_mode,
            'retrieval_scores': retrieval_scores,
            'faithfulness': faithfulness,
            'grounded': None if grounding is None else grounding.grounded,
            'abstained': None if grounding is None else grounding.abstained,
            'latency_ms': {
                'retrieval': round(retrieval_ms, 1),
                'llm': round(llm_ms, 1),
            },
            'tokens': {
                'input': llm_stats.get('input_tokens', 0),
                'output': llm_stats.get('output_tokens', 0),
                'per_sec': llm_stats.get('tokens_per_sec', 0.0),
            },
            'models_active': {
                'llm': llm_stats.get('model') if response_mode == 'llm' else None,
                'embedding': self._retrieval_config.get('dense_model') if search_mode in ('dense', 'hybrid', 'hybrid_rerank') else None,
                'reranker': self._retrieval_config.get('reranker_model') if search_mode == 'hybrid_rerank' else None,
            },
            'query_expansion': [],
        }
        return payload

    def _generate_template_response(
        self,
        query: str,
        results: List[Dict],
        language: str
    ) -> str:
        """Generate template-based response in the requested language"""
        if not results:
            not_found_messages = {
                'ru': f"К сожалению, я не нашел информацию по запросу '{query}'. Обратитесь в администрацию КубГУ: +7-861-XXX-XXXX или посетите https://kubsu.ru",
                'es': f"No encontré información sobre '{query}'. Contacte a la administración de KubGU: +7-861-XXX-XXXX o visite https://kubsu.ru",
                'en': f"Sorry, I couldn't find information about '{query}'. Contact KubGU administration: +7-861-XXX-XXXX or visit https://kubsu.ru",
                'fr': f"Désolé, je n'ai pas trouvé d'informations sur '{query}'. Contactez l'administration de KubGU: +7-861-XXX-XXXX ou visitez https://kubsu.ru"
            }
            return not_found_messages.get(language, not_found_messages['en'])

        best_match = results[0]
        content = best_match.get('content', '')
        source = best_match.get('source', 'KubGU')
        source_url = best_match.get('source_url', 'https://kubsu.ru')

        # Translate content if language is not Russian and translator is available
        if language != 'ru' and TRANSLATOR_AVAILABLE:
            translator = get_translator()
            if translator and translator.has_translator:
                try:
                    content = translator.translate_text(content, language)
                except Exception as e:
                    print(f"[RAG] Translation failed: {e}, using original content")

        templates = {
            'ru': f"""📌 ОФИЦИАЛЬНАЯ ИНФОРМАЦИЯ: {query}

📄 Источник: {source}

{content}

🔗 Подробнее: {source_url}""",
            'es': f"""📌 INFORMACIÓN OFICIAL: {query}

📄 Fuente: {source}

{content}

🔗 Más información: {source_url}""",
            'en': f"""📌 OFFICIAL INFORMATION: {query}

📄 Source: {source}

{content}

🔗 More info: {source_url}""",
            'fr': f"""📌 INFORMATION OFFICIELLE: {query}

📄 Source: {source}

{content}

🔗 Plus d'infos: {source_url}"""
        }

        return templates.get(language, templates['en'])

    def generate_stream(
        self,
        query: str,
        context_type: str = "general",
        language: str = "ru",
        session_id: str = None
    ) -> Generator[str, None, None]:
        """
        Generate streaming response using LLM

        Yields tokens/chunks as they are generated
        """
        # Search for documents first
        results = self.document_library.search(query)

        if self.is_llm_enabled():
            yield from self.llm.generate_stream(
                query=query,
                context_docs=results,
                language=language,
                session_id=session_id
            )
        else:
            yield self._generate_template_response(query, results, language)

    async def generate_stream_async(
        self,
        query: str,
        context_type: str = "general",
        language: str = "ru",
        session_id: str = None
    ) -> AsyncGenerator[str, None]:
        """
        Async streaming generation for FastAPI StreamingResponse
        """
        # Search for documents first
        results = self.document_library.search(query)

        if self.is_llm_enabled():
            async for token in self.llm.generate_stream_async(
                query=query,
                context_docs=results,
                language=language,
                session_id=session_id
            ):
                yield token
        else:
            yield self._generate_template_response(query, results, language)

    def get_recommendation(self, user_profile: Dict) -> Dict:
        """Get personalized recommendation based on profile"""
        country = user_profile.get('country', 'Unknown')
        visa_type = user_profile.get('visa_type', 'student')

        # Personalized searches
        searches = [
            "Регистрация по месту пребывания",
            "Медицинское страхование",
            "Общежитие для иностранных студентов"
        ]

        recommendations = []
        for search_query in searches:
            result = self.search_and_generate(
                search_query,
                context_type=f"profile_{country}",
                language="ru"
            )
            recommendations.append(result)

        return {
            'user_country': country,
            'visa_type': visa_type,
            'recommendations': recommendations
        }

    # ==================== Conversation History ====================

    def add_message(self, session_id: str, role: str, content: str):
        """Add message to conversation history"""
        if self.llm:
            self.llm.add_message(session_id, role, content)

    def get_history(self, session_id: str) -> List[Dict]:
        """Get conversation history for session"""
        if self.llm:
            return self.llm.get_history(session_id)
        return []

    def clear_history(self, session_id: str):
        """Clear conversation history for session"""
        if self.llm:
            self.llm.clear_session(session_id)

    def export_to_json(self, output_path: Path):
        """Export document library to JSON"""
        export_data = {
            'sources': list(self.document_library.documents.keys()),
            'documents': self.document_library.documents
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        return output_path


def create_rag_database():
    """Create enhanced RAG database"""
    rag = EnhancedRAGModule()
    return rag


if __name__ == "__main__":
    # Test del módulo
    rag = create_rag_database()

    print(f"🔍 Search mode: {rag.document_library.get_search_mode()}")
    print("\n🔍 PRUEBAS DE BÚSQUEDA:\n")

    test_queries = [
        "Регистрация иностранцев",
        "Общежитие",
        "Медицинский полис",
        "Виза для студента",
        "How to register in Russia"  # Semantic search should handle this
    ]

    for query in test_queries:
        result = rag.search_and_generate(query)
        print(f"Query: {query}")
        print(f"Search mode: {result.get('search_mode', 'unknown')}")
        print(result['response'][:500])
        print("\n" + "="*60 + "\n")
