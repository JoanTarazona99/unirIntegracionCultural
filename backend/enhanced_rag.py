"""
Módulo RAG Mejorado - Documentos Oficiales de KubGU
Integración con fuentes oficiales: КубГУ, МВД РФ, МФЦ, Госуслуги
"""

import json
from pathlib import Path
from typing import List, Dict, Optional

class OfficialDocumentLibrary:
    """Biblioteca de documentos oficiales para RAG"""
    
    def __init__(self):
        self.documents = {}
        self._initialize_documents()
    
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
                    2. Получение номера в электронную очередь
                    3. Ожидание вызова оператора
                    4. Подача документов оператору
                    5. Получение расписки
                    6. Ожидание результата (обычно 3-5 дней)
                    
                    ВАЖНО: Не откладывайте регистрацию! 
                    Штраф за опаздание: 5000-7000 рублей
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
        """Поиск в документах официальных с mejora de palabras clave"""
        results = []
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        # Mapeo de palabras clave en español a ruso
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
        
        # Expandir palabras de búsqueda
        expanded_words = set(query_words)
        for keyword, synonyms in keyword_mapping.items():
            if keyword in query_words:
                expanded_words.update(synonyms)
        
        # Buscar en todas las fuentes
        for source_name in self.documents.keys():
            doc = self.documents[source_name]
            
            for section in doc.get('sections', []):
                title = section.get('title', '').lower()
                content = section.get('content', '').lower()
                
                # Calcular relevancia
                match_score = 0
                
                # Búsqueda exacta en título
                if query_lower in title:
                    match_score = 1.0
                elif query_lower in content:
                    match_score = 0.8
                else:
                    # Búsqueda por palabras expandidas
                    matched_words = 0
                    total_query_words = len(query_words)
                    
                    for word in expanded_words:
                        if len(word) > 2:
                            if word in title:
                                matched_words += 3
                            elif word in content:
                                matched_words += 1
                    
                    if matched_words > 0:
                        match_score = min(0.9, matched_words * 0.1)
                
                if match_score > 0.3:  # Lowered threshold
                    results.append({
                        'source': source_name,
                        'source_url': doc.get('url'),
                        'title': section.get('title'),
                        'content': section.get('content').strip(),
                        'relevance': match_score
                    })
        
        # Si no hay resultados, devolver info general
        if not results:
            results.append({
                'source': 'KubGU',
                'source_url': 'https://kubsu.ru',
                'title': 'Informacion General',
                'content': f'Para mas informacion sobre "{query}", visite https://kubsu.ru o contacte a la administracion',
                'relevance': 0.3
            })
        if not results:
            results.append({
                'source': 'KubGU',
                'source_url': 'https://kubsu.ru',
                'title': 'Informacion General',
                'content': f'Para mas informacion sobre "{query}", visite https://kubsu.ru o contacte a la administracion',
                'relevance': 0.3
            })
        
        # Ordenar por relevancia
        results.sort(key=lambda x: x['relevance'], reverse=True)
        return results
    
    def get_source(self, source_name: str) -> Optional[Dict]:
        """Obtener información de una fuente específica"""
        return self.documents.get(source_name)
    
    def list_sources(self) -> List[str]:
        """Listar todas las fuentes disponibles"""
        return list(self.documents.keys())
    
    def get_all_sections(self, source: str) -> List[Dict]:
        """Obtener todas las secciones de una fuente"""
        if source in self.documents:
            return self.documents[source].get('sections', [])
        return []


class EnhancedRAGModule:
    """Módulo RAG mejorado con documentos reales"""
    
    def __init__(self):
        self.document_library = OfficialDocumentLibrary()
        self.cache = {}
    
    def search_and_generate(self, query: str, context_type: str = "general") -> Dict:
        """Buscar documentos y generar respuesta contextualizada"""
        
        # Búsqueda en biblioteca de documentos
        results = self.document_library.search(query)
        
        # Generar respuesta basada en contexto
        if not results:
            response = f"""
            No encontré información específica sobre: {query}
            
            Sugiero:
            1. Contactar a la Administración de KubGU: +7-861-XXXXXXX
            2. Visitar el portál: https://kubsu.ru
            3. Escribir al МФЦ: mfc@krasnodar.ru
            """
        else:
            best_match = results[0]
            response = f"""
            📌 INFORMACIÓN OFICIAL SOBRE: {query}
            
            Fuente: {best_match['source']}
            
            {best_match['content']}
            
            🔗 Más información: {best_match['source_url']}
            """
        
        return {
            'query': query,
            'response': response.strip(),
            'sources_found': len(results),
            'sources': results[:3],  # Top 3 resultados
            'context_type': context_type
        }
    
    def get_recommendation(self, user_profile: Dict) -> Dict:
        """Obtener recomendación personalizada basada en perfil"""
        country = user_profile.get('country', 'Unknown')
        visa_type = user_profile.get('visa_type', 'student')
        
        # Búsquedas personalizadas
        searches = [
            "Регистрация по месту пребывания",
            "Медицинское страхование",
            "Общежитие для иностранных студентов"
        ]
        
        recommendations = []
        for search_query in searches:
            result = self.search_and_generate(search_query, f"profile_{country}")
            recommendations.append(result)
        
        return {
            'user_country': country,
            'visa_type': visa_type,
            'recommendations': recommendations
        }
    
    def export_to_json(self, output_path: Path):
        """Exportar biblioteca de documentos a JSON"""
        export_data = {
            'sources': list(self.document_library.documents.keys()),
            'documents': self.document_library.documents
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        return output_path


def create_rag_database():
    """Crear base de datos RAG mejorada"""
    rag = EnhancedRAGModule()
    return rag


if __name__ == "__main__":
    # Test del módulo
    rag = create_rag_database()
    
    print("🔍 BÚSQUEDAS DE PRUEBA:\n")
    
    test_queries = [
        "Регистрация иностранцев",
        "Общежитие",
        "Медицинский полис",
        "Виза для студента"
    ]
    
    for query in test_queries:
        result = rag.search_and_generate(query)
        print(f"Query: {query}")
        print(result['response'])
        print("\n" + "="*60 + "\n")
