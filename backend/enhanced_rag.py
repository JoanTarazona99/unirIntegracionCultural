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

# Try to import sentence-transformers for semantic search
SEMANTIC_SEARCH_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer
    SEMANTIC_SEARCH_AVAILABLE = True
    print("[RAG] sentence-transformers loaded successfully - Semantic search enabled")
except ImportError:
    print("[RAG] sentence-transformers not available - Using keyword fallback")


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
                self.model = SentenceTransformer(model_name)
                self._initialized = True
                print("[RAG] Semantic search engine initialized successfully")
            except Exception as e:
                print(f"[RAG] Error loading model: {e}")
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
        if SEMANTIC_SEARCH_AVAILABLE:
            try:
                self.semantic_engine = SemanticSearchEngine()
                if self.semantic_engine._initialized:
                    # Flatten documents for embedding
                    self._flatten_documents()
                    # Build the index
                    if self.semantic_engine.build_index(self.flat_documents):
                        self._use_semantic = True
                        print("[RAG] Semantic search mode activated")
            except Exception as e:
                print(f"[RAG] Semantic search initialization failed: {e}")
                self._use_semantic = False
        else:
            print("[RAG] Using keyword search mode")

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
            'donde': ['направление', 'адрес', 'локация', 'donde'],
            'como': ['как', 'процесс', 'procedimiento', 'como'],
            'informacion': ['информация', 'info', 'informacion'],
            'gastos': ['стоимость', 'цена', 'gastos'],
            'costo': ['стоимость', 'руб', 'costo']
        }

        # Expand query words with synonyms
        expanded_words = set(query_words)
        for keyword, synonyms in keyword_mapping.items():
            if keyword in query_words:
                expanded_words.update(synonyms)

        # Search in all documents
        for source_name in self.documents.keys():
            doc = self.documents[source_name]

            for section in doc.get('sections', []):
                title = section.get('title', '').lower()
                content = section.get('content', '').lower()

                # Calculate relevance score
                match_score = 0

                if query_lower in title:
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

        # Search in document library
        results = self.document_library.search(query)

        # Get search mode
        search_mode = self.document_library.get_search_mode()

        # Determine response mode
        response_mode = "template"
        response = None

        # Try LLM first if available and enabled
        if use_llm and self.is_llm_enabled():
            try:
                response = self.llm.generate_response(
                    query=query,
                    context_docs=results,
                    language=language,
                    session_id=session_id
                )
                response_mode = "llm"
            except Exception as e:
                print(f"[RAG] LLM generation failed: {e}")
                response = None

        # Fallback to template response
        if response is None:
            response = self._generate_template_response(query, results, language)
            response_mode = "template"

        return {
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
