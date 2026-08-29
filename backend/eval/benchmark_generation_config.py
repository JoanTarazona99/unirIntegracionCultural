"""Deterministic configuration for the extended synthetic benchmark."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Dict, Tuple

GENERATOR_VERSION = "template-grounded-v2"
DEFAULT_SEED = 42
LANGUAGES = ("es", "en", "ru")
ANNOTATION_STATUS = "synthetic_needs_human_review"
LEGACY_STATUS = "needs_human_review"


@dataclass(frozen=True)
class TopicSpec:
    fragment_id: str
    category: str
    es: str
    en: str
    ru: str


TOPICS: Tuple[TopicSpec, ...] = (
    TopicSpec("КубГУ::0", "education", "la admisión de estudiantes extranjeros en KubGU", "international student admission at KubGU", "поступление иностранных студентов в КубГУ"),
    TopicSpec("КубГУ::1", "housing", "las condiciones de la residencia universitaria de KubGU", "conditions in the KubGU student dormitory", "условия проживания в общежитии КубГУ"),
    TopicSpec("КубГУ::2", "education", "la duración, los exámenes y las calificaciones de los programas de KubGU", "program duration, examinations, and grading at KubGU", "сроки обучения, экзамены и оценки в КубГУ"),
    TopicSpec("КубГУ::3", "admin", "la ubicación y los contactos del campus principal de KubGU", "the location and contact details of the main KubGU campus", "адрес и контакты главного корпуса КубГУ"),
    TopicSpec("КубГУ::4", "education", "la matrícula y los costos académicos de KubGU", "tuition and academic costs at KubGU", "стоимость обучения в КубГУ"),
    TopicSpec("МВД РФ::0", "migration", "el registro migratorio después de llegar a Rusia", "migration registration after arriving in Russia", "миграционная регистрация после приезда в Россию"),
    TopicSpec("МВД РФ::1", "visa", "los tipos y requisitos de la visa de estudiante", "student visa types and requirements", "виды и требования студенческой визы"),
    TopicSpec("МВД РФ::2", "legal_rights", "los derechos y obligaciones de un estudiante extranjero en Rusia", "the rights and obligations of an international student in Russia", "права и обязанности иностранного студента в России"),
    TopicSpec("МФЦ::0", "admin", "el registro de extranjeros a través del MFC", "foreigner registration through the MFC", "регистрация иностранцев через МФЦ"),
    TopicSpec("МФЦ::1", "health", "la obtención de una póliza médica OMS", "obtaining an OMS medical insurance policy", "получение медицинского полиса ОМС"),
    TopicSpec("МФЦ::2", "admin", "los certificados y constancias disponibles en el MFC", "certificates and official statements available at the MFC", "справки и свидетельства, доступные в МФЦ"),
    TopicSpec("Госуслуги::0", "admin", "el registro de extranjeros en el portal Gosuslugi", "foreigner registration on the Gosuslugi portal", "регистрация иностранца на портале Госуслуги"),
    TopicSpec("Госуслуги::1", "admin", "la reserva electrónica de citas en servicios públicos", "online appointments for public services", "электронная запись на приём в государственные службы"),
    TopicSpec("Госуслуги::2", "visa", "la documentación para una visa de estudiante rusa", "documents for a Russian student visa", "документы для студенческой визы в Россию"),
    TopicSpec("FAQ::0", "admin", "las direcciones y horarios del MFC en Krasnodar", "MFC addresses and opening hours in Krasnodar", "адреса и часы работы МФЦ в Краснодаре"),
    TopicSpec("FAQ::1", "admin", "el procedimiento paso a paso de registro en el MFC", "the step-by-step registration procedure at the MFC", "пошаговая процедура регистрации в МФЦ"),
    TopicSpec("FAQ::2", "housing", "el costo y las reglas del dormitorio para estudiantes extranjeros", "dormitory costs and rules for international students", "стоимость и правила общежития для иностранных студентов"),
    TopicSpec("FAQ::3", "health", "el proceso y costo del seguro médico para estudiantes", "the process and cost of student medical insurance", "оформление и стоимость медицинской страховки для студентов"),
    TopicSpec("FAQ::4", "language", "el nivel de ruso requerido para estudiar en KubGU", "the Russian level required to study at KubGU", "уровень русского языка для учёбы в КубГУ"),
    TopicSpec("ГУВМ МВД::0", "migration", "el uso y conservación de la tarjeta de migración", "using and keeping the migration card", "использование и хранение миграционной карты"),
    TopicSpec("ГУВМ МВД::1", "visa", "la prórroga anual de la visa de estudiante", "annual student visa renewal", "ежегодное продление студенческой визы"),
    TopicSpec("ГУВМ МВД::2", "employment", "las condiciones para trabajar mientras se estudia en Rusia", "conditions for working while studying in Russia", "условия работы во время учёбы в России"),
    TopicSpec("Здравоохранение::0", "health", "el examen médico obligatorio para estudiantes extranjeros", "the mandatory medical examination for international students", "обязательный медосмотр иностранных студентов"),
    TopicSpec("Здравоохранение::1", "health", "la atención en una policlínica con seguro médico", "receiving care at a polyclinic with medical insurance", "обращение в поликлинику с медицинским полисом"),
    TopicSpec("Банк::0", "finance", "la apertura de una cuenta bancaria en Rusia", "opening a bank account in Russia", "открытие банковского счёта в России"),
    TopicSpec("Банк::1", "finance", "los pagos y transferencias bancarias mediante SBP", "bank payments and transfers through SBP", "банковские платежи и переводы через СБП"),
    TopicSpec("Документы РФ::0", "finance", "la obtención y el uso del número fiscal INN", "obtaining and using an INN tax number", "получение и использование ИНН"),
    TopicSpec("Документы РФ::1", "finance", "la obtención y el uso del número de seguro SNILS", "obtaining and using a SNILS insurance number", "получение и использование СНИЛС"),
    TopicSpec("Транспорт::0", "transport", "el transporte público y sus formas de pago en Krasnodar", "public transport and payment methods in Krasnodar", "общественный транспорт и способы оплаты в Краснодаре"),
    TopicSpec("Транспорт::1", "transport", "el uso seguro de taxis y coche compartido", "using taxis and car sharing safely", "безопасное использование такси и каршеринга"),
    TopicSpec("Мобильная связь::0", "communication", "la compra y activación de una tarjeta SIM rusa", "buying and activating a Russian SIM card", "покупка и активация российской SIM-карты"),
    TopicSpec("Мобильная связь::1", "communication", "las tarifas móviles y el acceso a Internet", "mobile plans and Internet access", "мобильные тарифы и доступ в интернет"),
    TopicSpec("Безопасность::0", "safety", "los números de emergencia en Rusia", "emergency telephone numbers in Russia", "телефоны экстренных служб в России"),
    TopicSpec("Безопасность::1", "safety", "las acciones necesarias al perder documentos", "steps to take after losing personal documents", "действия при потере документов"),
    TopicSpec("Стипендии::0", "scholarships", "los tipos y requisitos de las becas estudiantiles", "types and requirements of student scholarships", "виды и требования студенческих стипендий"),
    TopicSpec("Адаптация::0", "cultural_adaptation", "la adaptación cultural y práctica a la vida en Krasnodar", "cultural and practical adaptation to life in Krasnodar", "культурная и бытовая адаптация к жизни в Краснодаре"),
    TopicSpec("Адаптация::1", "cultural_adaptation", "las principales fiestas y tradiciones rusas", "major Russian holidays and traditions", "основные российские праздники и традиции"),
    TopicSpec("Русский язык::0", "language", "los niveles y usos del certificado TRKI", "TRKI certificate levels and uses", "уровни и применение сертификата ТРКИ"),
    TopicSpec("Русский язык::1", "language", "los exámenes internacionales de idiomas aceptados por KubGU", "international language examinations accepted by KubGU", "международные языковые экзамены, принимаемые КубГУ"),
    TopicSpec("Жильё::0", "housing", "el alquiler privado de un apartamento en Krasnodar", "renting a private apartment in Krasnodar", "аренда частной квартиры в Краснодаре"),
    TopicSpec("Питание::0", "food", "los comedores universitarios y opciones económicas de comida", "university canteens and affordable food options", "университетские столовые и недорогие варианты питания"),
    TopicSpec("Документы::0", "documents", "los documentos legales exigidos a estudiantes extranjeros", "legal documents required from international students", "официальные документы для иностранных студентов"),
    TopicSpec("Документы::1", "documents", "la traducción notarial de documentos en Krasnodar", "notarized document translation in Krasnodar", "нотариальный перевод документов в Краснодаре"),
    TopicSpec("Документы::2", "documents", "la tramitación conjunta de SNILS e INN", "applying for SNILS and INN", "оформление СНИЛС и ИНН"),
)

LANGUAGE_TARGETS: Dict[str, int] = {language: len(TOPICS) for language in LANGUAGES}
CATEGORY_TARGETS: Dict[str, int] = dict(
    sorted(Counter(topic.category for topic in TOPICS for _ in LANGUAGES).items())
)

QUESTION_TEMPLATES = {
    "es": (
        "¿Qué información se proporciona sobre {topic}?",
        "¿Qué datos importantes se presentan sobre {topic}?",
        "¿Qué debe saber un estudiante extranjero sobre {topic}?",
    ),
    "en": (
        "What information is provided about {topic}?",
        "What key details are provided about {topic}?",
        "What should an international student know about {topic}?",
    ),
    "ru": (
        "Какая информация представлена по теме: «{topic}»?",
        "Какие сведения приведены по теме: «{topic}»?",
        "Что следует знать по теме: «{topic}»?",
    ),
}
