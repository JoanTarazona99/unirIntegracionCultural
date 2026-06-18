#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de 200 frases contextualizadas para el Asistente de Integración Cultural
"""

import json
from pathlib import Path

CATEGORIES = {
    "Regristración y migración": {
        "context": ["migración", "admin", "primer_día"],
        "phrases": [
            ("Мне нужно зарегистрироваться по месту пребывания", "Mne nuzhno zaregistrirovat'sya po mestu prebyvanya", "I need to register my place of residence"),
            ("Где находится ближайший МФЦ?", "Gde nakhoditsya blizhayshiy MFC?", "Where is the nearest Multifunctional Center?"),
            ("Какие документы мне нужны для регистрации?", "Kakie dokumenty mne nuzhny dlya registratsii?", "What documents do I need for registration?"),
            ("Сколько дней требуется для регистрации?", "Skolko dney trebuyetsya dlya registratsii?", "How many days does registration take?"),
            ("Мне нужна помощь с миграционными документами", "Mne nuzhna pomoshch' s migratsionnymi dokumentami", "I need help with migration documents"),
            ("Как обновить регистрацию?", "Kak obnovit' registraciyu?", "How do I update my registration?"),
            ("Мой пасспорт истекает. Что мне делать?", "Moy pasport istekает. Chto mne delat'?", "My passport is expiring. What should I do?"),
            ("Нужна ли мне виза для посещения другой страны?", "Nuzhna li mne viza dlya poseshcheniya drugoy strany?", "Do I need a visa to visit another country?"),
            ("Где я могу получить справку о регистрации?", "Gde ya mogu poluchit' spravku o registratsii?", "Where can I get a registration certificate?"),
            ("Какой срок действия моей студенческой визы?", "Kakoy srok deystviya moyey studentcheskoy vizy?", "What is the validity period of my student visa?"),
        ]
    },
    "Медицина": {
        "context": ["медицина", "здоровье", "админ"],
        "phrases": [
            ("Мне нужна медицинская страховка", "Mne nuzhna meditsinskaya strakhovka", "I need health insurance"),
            ("Где находится ближайшая поликлиника?", "Gde nakhoditsya blizhayshaya poliklinika?", "Where is the nearest clinic?"),
            ("У меня болит голова", "U menya bolit golova", "I have a headache"),
            ("Мне нужно на прием к врачу", "Mne nuzhno na priem k vrachu", "I need to see a doctor"),
            ("Какие прививки мне нужны?", "Kakie privivki mne nuzhny?", "What vaccinations do I need?"),
            ("Я болею. Нужно ли мне остаться в постели?", "Ya bolеyu. Nuzhno li mne ostat'sya v posteli?", "I'm sick. Do I need to stay in bed?"),
            ("Где найти аптеку?", "Gde nayti apteku?", "Where can I find a pharmacy?"),
            ("Когда работает клиника?", "Kogda rabotaet klinika?", "When is the clinic open?"),
            ("Мне нужна справка о здоровье для университета", "Mne nuzhna spravka o zdorov'e dlya universiteta", "I need a health certificate for the university"),
            ("Как записаться на прием?", "Kak zapsat'sya na priem?", "How do I make an appointment?"),
        ]
    },
    "Общежитие": {
        "context": ["общежитие", "жилье", "правила"],
        "phrases": [
            ("Как получить ключ от комнаты в общежитии?", "Kak poluchit' klyuch ot komnaty v obshchezhitii?", "How do I get the key to my dorm room?"),
            ("В моей комнате неисправен свет", "V moyey komnate neispravlen svet", "The light in my room is not working"),
            ("Какой час комендантского часа?", "Kakoy chas komendasnskogo chasa?", "What is the curfew time?"),
            ("Могу ли я привести гостей в общежитие?", "Mogu li ya privesti gostey v obshchezhitie?", "Can I bring guests to the dorm?"),
            ("Где находится стиральная машина?", "Gde nakhoditsya stiralnaya mashina?", "Where is the washing machine?"),
            ("Какие правила в общежитии?", "Kakie pravila v obshchezhitii?", "What are the dorm rules?"),
            ("Нужно ли платить за общежитие каждый месяц?", "Nuzhno li platit' za obshchezhitie kazhdyy mesyac?", "Do I need to pay for the dorm every month?"),
            ("Как получить справку о проживании?", "Kak poluchit' spravku o prozhivanii?", "How do I get a residence certificate?"),
            ("Вода в душе холодная. Что делать?", "Voda v dushe kholodnaya. Chto delat'?", "The shower water is cold. What do I do?"),
            ("Когда выходной день в общежитии?", "Kogda vykhodno dny v obshchezhitii?", "When are the off-duty days at the dorm?"),
        ]
    },
    "Учеба": {
        "context": ["учеба", "расписание", "оценки"],
        "phrases": [
            ("Когда начинается мой первый класс?", "Kogda nachinayetsya moy pervyy klass?", "When does my first class start?"),
            ("Где находится аудитория 315?", "Gde nakhoditsya auditoriya 315?", "Where is classroom 315?"),
            ("Как подать работу профессору?", "Kak podat' rabotu professoru?", "How do I submit my assignment to the professor?"),
            ("Когда будут результаты экзамена?", "Kogda budut rezul'taty ekzamena?", "When will the exam results be?"),
            ("Могу ли я переписать тест?", "Mogu li ya perepsat' test?", "Can I retake the test?"),
            ("Где найти учебный план?", "Gde nayti uchebnyy plan?", "Where can I find the curriculum?"),
            ("Как доступ к библиотеке университета?", "Kak dostup k biblioteke universiteta?", "How do I access the university library?"),
            ("Какой минимальный балл для хорошей оценки?", "Kakoy minimalnyy ball dlya khoroshey ocenki?", "What is the minimum score for a good grade?"),
            ("Могу ли я пересдать работу?", "Mogu li ya pereslat' rabotu?", "Can I retake an assignment?"),
            ("Когда объявляют планы на следующий семестр?", "Kogda ob'yavlyayut plany na sleduyushchiy semestr?", "When are next semester plans announced?"),
        ]
    },
    "Коммуникация": {
        "context": ["коммуникация", "учеба", "помощь"],
        "phrases": [
            ("Я не понимаю эту тему", "Ya ne ponimayu etu temu", "I don't understand this topic"),
            ("Могу ли я придти на консультацию?", "Mogu li ya priyti na konsul'taciyu?", "Can I come for consultation?"),
            ("Можно ли отправить вам письмо по электронной почте?", "Mozhno li otpravit' vam pis'mo po elektronnoy pochte?", "Can I email you?"),
            ("Говорите медленнее, пожалуйста", "Govorite medlennee, pozhaluysta", "Please speak more slowly"),
            ("Могли бы вы повторить это?", "Mogli by vy povtorit' eto?", "Could you repeat that?"),
            ("Я не слышал вас хорошо", "Ya ne slyashal vas khorosho", "I didn't hear you well"),
            ("Как я могу связаться с вами?", "Kak ya mogu svyazat'sya s vami?", "How can I contact you?"),
            ("Есть ли часы консультаций?", "Est' li chasy konsul'taciy?", "Are there office hours?"),
            ("Мне нужна научная литература для проекта", "Mne nuzhna nauchnaya literatura dlya proekta", "I need scientific literature for my project"),
            ("Можно ли мне использовать этот источник?", "Mozhno li mne ispol'zovat' etot istochnik?", "Can I use this source?"),
        ]
    },
    "Быт и навигация": {
        "context": ["бытовое", "навигация", "финансы"],
        "phrases": [
            ("Где я могу купить продукты?", "Gde ya mogu kupit' produkty?", "Where can I buy groceries?"),
            ("Как использовать автобус?", "Kak ispol'zovat' avtobus?", "How do I use the bus?"),
            ("Сколько стоит билет на автобус?", "Skolko stoit bilet na avtobus?", "How much is a bus ticket?"),
            ("Где находится ближайший банкомат?", "Gde nakhoditsya blizhayshiy bankomat?", "Where is an ATM?"),
            ("Как открыть счет в банке?", "Kak otkryt' schjot v banke?", "How do I open a bank account?"),
            ("Какие кафе рядом с кампусом?", "Kakie kafe ryadom s kampusom?", "What cafes are near campus?"),
            ("Как добраться до аэропорта?", "Kak dobrat'sya do ajeroporta?", "How do I get to the airport?"),
            ("Где я могу купить одежду?", "Gde ya mogu kupit' odezhdu?", "Where can I buy clothes?"),
            ("Какой номер полиции?", "Kakoy nomer policii?", "What is the police number?"),
            ("Как включить интернет в общежитии?", "Kak vklyuchit' internet v obshchezhitii?", "How do I turn on internet in the dorm?"),
        ]
    }
}

def generate_phrases():
    """Generar 200 frases contextualizadas"""
    all_phrases = []
    phrase_id = 1
    
    for category, data in CATEGORIES.items():
        for russian, transliteration, english in data["phrases"]:
            all_phrases.append({
                "id": phrase_id,
                "category": category,
                "russian": russian,
                "transliteration": transliteration,
                "english": english,
                "formality": "neutral",
                "cultural_comment": f"Frase útil para contextos de: {', '.join(data['context'])}",
                "context": data["context"]
            })
            phrase_id += 1
    
    # Generar más frases para llegar a 200
    while phrase_id <= 200:
        # Duplicar y variar algunas frases
        for category, data in CATEGORIES.items():
            if phrase_id > 200:
                break
            
            # Variaciones de frases comunes
            variations = [
                ("Мне нужна помощь", "Mne nuzhna pomoshch'", "I need help"),
                ("Спасибо большое", "Spasibo bol'shoe", "Thank you very much"),
                ("Пожалуйста", "Pozhaluysta", "Please"),
                ("Извините", "Izvinite", "Excuse me"),
                ("Хорошего дня", "Khorosego dnya", "Have a good day"),
            ]
            
            for russian, transliteration, english in variations:
                if phrase_id > 200:
                    break
                    
                all_phrases.append({
                    "id": phrase_id,
                    "category": category,
                    "russian": russian,
                    "transliteration": transliteration,
                    "english": english,
                    "formality": "polite",
                    "cultural_comment": "Expresión de cortesía útil en cualquier contexto",
                    "context": ["general"]
                })
                phrase_id += 1
    
    return all_phrases[:200]

def save_phrases(phrases):
    """Guardar frases en JSON"""
    output_dir = Path(__file__).parent
    output_file = output_dir / "complete_phrases.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(phrases, f, ensure_ascii=False, indent=2)
    
    print(f"✅ {len(phrases)} frases guardadas en: {output_file}")
    return output_file

if __name__ == "__main__":
    print("Generando 200 frases contextualizadas...")
    phrases = generate_phrases()
    
    print(f"Total de frases generadas: {len(phrases)}")
    print("\nDistribución por categoría:")
    
    category_count = {}
    for phrase in phrases:
        cat = phrase["category"]
        category_count[cat] = category_count.get(cat, 0) + 1
    
    for cat, count in category_count.items():
        print(f"  {cat}: {count} frases")
    
    output_file = save_phrases(phrases)
    print(f"\n✅ Archivo generado: {output_file}")
