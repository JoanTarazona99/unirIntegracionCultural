"""
Telegram Bot - Asistente de Integración Cultural KubGU
Full-featured bot with RAG integration, TTS, and conversation memory
"""

import logging
import os
import io
import json
import asyncio
from typing import Optional, Dict, List
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field

import aiohttp
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    BotCommand
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
SELECTING_COUNTRY, SELECTING_VISA, SELECTING_LEVEL = range(3)

# Backend API URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


@dataclass
class UserSession:
    """User session with preferences and conversation history"""
    user_id: int
    country: str = "Unknown"
    visa_type: str = "student"
    russian_level: str = "A1"
    language: str = "es"  # Preferred language: ru, es, en
    conversation_history: List[Dict] = field(default_factory=list)
    session_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        if not self.session_id:
            import uuid
            self.session_id = str(uuid.uuid4())[:8]

    def add_message(self, role: str, content: str):
        """Add message to conversation history (keep last 10)"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]

    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "country": self.country,
            "visa_type": self.visa_type,
            "russian_level": self.russian_level,
            "language": self.language,
            "session_id": self.session_id,
            "conversation_history": self.conversation_history
        }


class KubGUAssistantBot:
    """Bot de Telegram para Asistente de Integración Cultural"""

    def __init__(self, token: str):
        self.token = token
        self.app = None
        self.user_sessions: Dict[int, UserSession] = {}

        # HTTP session for API calls
        self._http_session: Optional[aiohttp.ClientSession] = None

        # System status cache
        self._system_status = None
        self._last_status_check = 0

    async def get_http_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._http_session

    async def close_http_session(self):
        """Close HTTP session"""
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()

    def get_user_session(self, user_id: int) -> UserSession:
        """Get or create user session"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = UserSession(user_id=user_id)
        return self.user_sessions[user_id]

    # ==================== API Integration Methods ====================

    async def call_backend_chat(self, query: str, session: UserSession) -> Dict:
        """Call backend /api/chat endpoint"""
        try:
            http = await self.get_http_session()

            payload = {
                "query": query,
                "user_id": str(session.user_id),
                "language": session.language,
                "session_id": session.session_id
            }

            async with http.post(
                f"{BACKEND_URL}/api/chat",
                json=payload
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Chat API error: {response.status}")
                    return {"error": f"API error: {response.status}"}

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error calling chat API: {e}")
            return {"error": f"Connection error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error in chat API call: {e}")
            return {"error": f"Error: {str(e)}"}

    async def call_backend_tts(self, text: str, language: str = "ru") -> Optional[bytes]:
        """Call backend /api/tts endpoint, return audio bytes"""
        try:
            http = await self.get_http_session()

            payload = {
                "text": text,
                "language": language
            }

            async with http.post(
                f"{BACKEND_URL}/api/tts",
                json=payload
            ) as response:
                if response.status == 200:
                    return await response.read()
                elif response.status == 503:
                    logger.warning("TTS service unavailable")
                    return None
                else:
                    logger.error(f"TTS API error: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error calling TTS API: {e}")
            return None

    async def get_backend_status(self) -> Dict:
        """Get system status from backend"""
        try:
            http = await self.get_http_session()

            async with http.get(f"{BACKEND_URL}/api/status") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"Status API error: {response.status}"}

        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {"error": f"Connection error: {str(e)}"}

    async def get_phrases_from_backend(self, limit: int = 10) -> List[Dict]:
        """Get phrases from backend"""
        try:
            http = await self.get_http_session()

            async with http.get(f"{BACKEND_URL}/api/phrases?limit={limit}") as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception as e:
            logger.error(f"Error getting phrases: {e}")
            return []

    # ==================== Command Handlers ====================

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.message.from_user.id
        user_name = update.message.from_user.first_name
        session = self.get_user_session(user_id)

        welcome_text = f"""
¡Hola {user_name}! 👋

Soy el Asistente Inteligente de Integración Cultural de KubGU.

*Funcionalidades:*
• /ask <pregunta> - Pregunta sobre trámites, visas, etc.
• /voice <texto> - Convierte texto a audio en ruso
• /status - Ver estado del sistema
• /lang <ru|es|en> - Cambiar idioma preferido
• /setup - Configurar tu perfil
• /phrases - Ver frases útiles

*Tu idioma actual:* {session.language.upper()}

Puedes escribir preguntas directamente y te responderé.
        """

        await update.message.reply_text(welcome_text, parse_mode="Markdown")
        logger.info(f"User {user_id} started bot")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
*📚 Comandos disponibles:*

*Chat & Consultas:*
/ask <pregunta> - Realizar pregunta al asistente
/status - Estado del sistema (RAG, LLM, TTS)
/lang <ru|es|en> - Cambiar idioma preferido

*Perfil:*
/profile - Ver tu perfil actual
/setup - Configurar perfil personalizado

*Contenido:*
/phrases - Ver frases útiles en ruso
/search <texto> - Buscar en documentos

*Audio:*
/voice <texto> - Convertir texto a voz (ruso)

*Ejemplos de preguntas:*
• ¿Dónde está el МФЦ?
• ¿Cómo registrarse?
• Documentos para visa
• Información sobre dormitorio
        """

        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def ask_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ask <question> command - calls backend RAG"""
        user_id = update.message.from_user.id
        session = self.get_user_session(user_id)

        if not context.args:
            await update.message.reply_text(
                "Uso: /ask <pregunta>\n\nEjemplo: /ask ¿Cómo registrarse en el МФЦ?"
            )
            return

        query = " ".join(context.args)

        # Show typing action while processing
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )

        # Call backend RAG
        result = await self.call_backend_chat(query, session)

        if "error" in result:
            await update.message.reply_text(
                f"❌ Error: {result['error']}\n\nIntenta nuevamente."
            )
            return

        # Update conversation history
        session.add_message("user", query)
        session.add_message("assistant", result.get("answer", ""))

        # Send response
        answer = result.get("answer", "No se encontró respuesta.")
        await update.message.reply_text(answer)

        # Show sources if available
        sources = result.get("context", [])
        if sources:
            source_text = "\n".join([f"📄 {s[:50]}..." for s in sources[:3]])
            await update.message.reply_text(f"📚 *Fuentes:*\n{source_text}", parse_mode="Markdown")

        logger.info(f"User {user_id} asked: {query[:50]}...")

    async def voice_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /voice <text> command - TTS"""
        user_id = update.message.from_user.id
        session = self.get_user_session(user_id)

        if not context.args:
            await update.message.reply_text(
                "Uso: /voice <texto>\n\nEjemplo: /voice Где находится МФЦ?"
            )
            return

        text = " ".join(context.args)

        # Determine language: use user's language if Russian, else default to Russian for TTS
        tts_lang = "ru" if session.language == "ru" else "ru"

        # Show typing while processing
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="upload_voice"
        )

        # Call TTS
        audio_data = await self.call_backend_tts(text, tts_lang)

        if audio_data is None:
            await update.message.reply_text(
                "⚠️ Servicio TTS no disponible.\n\n"
                "Asegúrate de que el backend está corriendo y gTTS está instalado."
            )
            return

        # Send audio file
        await update.message.reply_voice(
            voice=io.BytesIO(audio_data),
            caption=f"🔊 Audio ({tts_lang}): {text[:50]}..."
        )

        logger.info(f"User {user_id} generated TTS: {text[:30]}...")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command - shows system status"""
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )

        status = await self.get_backend_status()

        if "error" in status:
            await update.message.reply_text(
                f"❌ No se pudo conectar al backend.\n\nError: {status['error']}\n\n"
                f"Asegúrate de que el backend está corriendo en {BACKEND_URL}"
            )
            return

        # Format status
        rag_status = "✅" if status.get("rag", {}).get("available") else "⚠️"
        llm_status = "✅" if status.get("llm", {}).get("available") else "⚠️"
        tts_status = "✅" if status.get("tts", {}).get("available") else "⚠️"
        stt_status = "✅" if status.get("stt", {}).get("available") else "⚠️"
        cache_status = "✅" if status.get("cache", {}).get("available") else "⚠️"

        status_text = f"""
📊 *Estado del Sistema*

Backend: {BACKEND_URL}
Versión: {status.get('version', 'unknown')}

*Módulos:*
RAG (Search): {rag_status}
LLM (AI): {llm_status}
TTS (Audio): {tts_status}
STT (Voice): {stt_status}
Cache: {cache_status}

*Detalles:*
• Search mode: {status.get('rag', {}).get('mode', 'unknown')}
• LLM model: {status.get('llm', {}).get('model', 'none')}
• Cache entries: {status.get('cache', {}).get('entries', 0)}
        """

        await update.message.reply_text(status_text, parse_mode="Markdown")

    async def lang_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /lang <ru|es|en> command"""
        user_id = update.message.from_user.id
        session = self.get_user_session(user_id)

        if not context.args:
            await update.message.reply_text(
                f"Idioma actual: {session.language.upper()}\n\n"
                "Uso: /lang <ru|es|en>\n"
                "• ru - Русский\n"
                "• es - Español\n"
                "• en - English"
            )
            return

        new_lang = context.args[0].lower()
        if new_lang not in ['ru', 'es', 'en']:
            await update.message.reply_text(
                "Idioma no válido. Usa: ru, es, o en"
            )
            return

        session.language = new_lang
        lang_names = {'ru': 'Русский', 'es': 'Español', 'en': 'English'}

        await update.message.reply_text(
            f"✅ Idioma cambiado a: {lang_names[new_lang]} ({new_lang.upper()})"
        )
        logger.info(f"User {user_id} changed language to {new_lang}")

    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /profile command"""
        user_id = update.message.from_user.id
        session = self.get_user_session(user_id)

        profile_text = f"""
👤 *Tu Perfil:*

• País: {session.country}
• Visa: {session.visa_type}
• Nivel de ruso: {session.russian_level}
• Idioma preferido: {session.language.upper()}
• Session ID: {session.session_id}

Mensajes en historial: {len(session.conversation_history)}

Usa /setup para reconfigurar tu perfil.
        """

        await update.message.reply_text(profile_text, parse_mode="Markdown")

    async def phrases_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /phrases command"""
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )

        # Try to get phrases from backend first
        phrases = await self.get_phrases_from_backend(limit=5)

        if phrases:
            phrases_text = "🇷🇺 *Frases útiles:*\n\n"
            for p in phrases:
                russian = p.get('russian', '')
                translit = p.get('transliteration', '')
                english = p.get('english', '')
                phrases_text += f"• {russian}\n  ({translit})\n  {english}\n\n"
        else:
            # Fallback phrases
            phrases_text = """
🇷🇺 *Frases útiles:*

• Мне нужна помощь
  (Mne nuzhna pomoshch')
  Necesito ayuda

• Где находится...?
  (Gde nakhoditsya...?)
  ¿Dónde está...?

• Говорите медленнее
  (Govorite medlennee)
  Habla más lentamente

• Не понимаю
  (Ne ponimayu)
  No entiendo

• Спасибо
  (Spasibo)
  Gracias
            """

        await update.message.reply_text(phrases_text, parse_mode="Markdown")

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command - alias for /ask"""
        await self.ask_command(update, context)

    # ==================== Message Handler ====================

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle general messages - calls backend RAG"""
        user_id = update.message.from_user.id
        user_message = update.message.text
        session = self.get_user_session(user_id)

        logger.info(f"Message from {user_id}: {user_message[:50]}...")

        # Show typing action
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )

        # Call backend RAG
        result = await self.call_backend_chat(user_message, session)

        if "error" in result:
            await update.message.reply_text(
                f"⚠️ Error procesando tu mensaje.\n\n"
                f"Usa /ask <pregunta> o intenta más tarde.\n\n"
                f"Error: {result['error']}"
            )
            return

        # Update history
        session.add_message("user", user_message)
        answer = result.get("answer", "")
        session.add_message("assistant", answer)

        # Send response
        await update.message.reply_text(answer)

    # ==================== Conversation Handlers for Setup ====================

    async def setup_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start profile setup"""
        keyboard = [
            [
                InlineKeyboardButton("🇻🇳 Vietnam", callback_data="setup_country_vietnam"),
                InlineKeyboardButton("🇨🇳 China", callback_data="setup_country_china")
            ],
            [
                InlineKeyboardButton("🇰🇿 Kazakhstan", callback_data="setup_country_kazakhstan"),
                InlineKeyboardButton("🇦🇲 Armenia", callback_data="setup_country_armenia")
            ],
            [
                InlineKeyboardButton("🇸🇾 Syria", callback_data="setup_country_syria"),
                InlineKeyboardButton("🌍 Otro", callback_data="setup_country_other")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "¿De qué país eres?",
            reply_markup=reply_markup
        )

        return SELECTING_COUNTRY

    async def select_country(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle country selection"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        country_data = query.data.replace("setup_country_", "")
        session = self.get_user_session(user_id)
        session.country = country_data.title()

        keyboard = [
            [
                InlineKeyboardButton("📚 Estudiante", callback_data="setup_visa_student"),
                InlineKeyboardButton("🔄 Intercambio", callback_data="setup_visa_exchange")
            ],
            [
                InlineKeyboardButton("✈️ Visitante", callback_data="setup_visa_visit")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=f"País: {session.country}\n\n¿Qué tipo de visa tienes?",
            reply_markup=reply_markup
        )

        return SELECTING_VISA

    async def select_visa(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle visa selection"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        visa_data = query.data.replace("setup_visa_", "")
        session = self.get_user_session(user_id)
        session.visa_type = visa_data

        keyboard = [
            [
                InlineKeyboardButton("A1-A2", callback_data="setup_level_a1"),
                InlineKeyboardButton("B1", callback_data="setup_level_b1")
            ],
            [
                InlineKeyboardButton("B2", callback_data="setup_level_b2"),
                InlineKeyboardButton("C1+", callback_data="setup_level_c1")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=f"País: {session.country}\nVisa: {session.visa_type}\n\n¿Cuál es tu nivel de ruso?",
            reply_markup=reply_markup
        )

        return SELECTING_LEVEL

    async def select_level(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle level selection - finish setup"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        level_data = query.data.replace("setup_level_", "").upper()
        session = self.get_user_session(user_id)
        session.russian_level = level_data

        confirmation = f"""
✅ ¡Perfil configurado!

• País: {session.country}
• Visa: {session.visa_type}
• Nivel de ruso: {session.russian_level}
• Idioma: {session.language.upper()}

Ahora puedo darte recomendaciones personalizadas.
Usa /ask para hacer preguntas.
        """

        await query.edit_message_text(text=confirmation)
        logger.info(f"Profile created for user {user_id}: {session.to_dict()}")

        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel setup"""
        await update.message.reply_text("❌ Configuración cancelada.")
        return ConversationHandler.END

    # ==================== Callback Query Handler ====================

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all inline button callbacks"""
        query = update.callback_query
        await query.answer()

        data = query.data
        user_id = query.from_user.id

        # Handle language buttons
        if data.startswith("lang_"):
            lang = data.replace("lang_", "")
            session = self.get_user_session(user_id)
            if lang in ['ru', 'es', 'en']:
                session.language = lang
                await query.edit_message_text(
                    text=f"✅ Idioma cambiado a: {lang.upper()}"
                )

        # Handle phrase navigation
        elif data.startswith("phrase_"):
            phrase_id = data.replace("phrase_", "")
            # Could implement phrase pagination here
            await query.answer("Frases mostradas")

        else:
            await query.answer("Botón no implementado")

    # ==================== Initialization ====================

    def initialize(self):
        """Initialize bot application"""
        self.app = Application.builder().token(self.token).build()

        # Command handlers
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("ask", self.ask_command))
        self.app.add_handler(CommandHandler("voice", self.voice_command))
        self.app.add_handler(CommandHandler("status", self.status_command))
        self.app.add_handler(CommandHandler("lang", self.lang_command))
        self.app.add_handler(CommandHandler("profile", self.profile_command))
        self.app.add_handler(CommandHandler("phrases", self.phrases_command))
        self.app.add_handler(CommandHandler("search", self.search_command))

        # Message handler for non-command text
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Callback query handler for inline buttons
        self.app.add_handler(CallbackQueryHandler(self.handle_callback_query))

        # Conversation handler for setup
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("setup", self.setup_start)],
            states={
                SELECTING_COUNTRY: [CallbackQueryHandler(self.select_country, pattern="^setup_country_")],
                SELECTING_VISA: [CallbackQueryHandler(self.select_visa, pattern="^setup_visa_")],
                SELECTING_LEVEL: [CallbackQueryHandler(self.select_level, pattern="^setup_level_")],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        self.app.add_handler(conv_handler)

        # Set bot commands
        async def set_commands(application):
            commands = [
                BotCommand("start", "Iniciar el bot"),
                BotCommand("help", "Ver ayuda"),
                BotCommand("ask", "Hacer pregunta al asistente"),
                BotCommand("voice", "Convertir texto a audio"),
                BotCommand("status", "Estado del sistema"),
                BotCommand("lang", "Cambiar idioma"),
                BotCommand("profile", "Ver perfil"),
                BotCommand("phrases", "Ver frases útiles"),
                BotCommand("setup", "Configurar perfil"),
            ]
            await application.bot.set_my_commands(commands)

        self.app.post_init = set_commands


def main():
    """Main function"""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE").strip()

    if not token or token == "YOUR_BOT_TOKEN_HERE":
        logger.error("Configura TELEGRAM_BOT_TOKEN en variables de entorno")
        logger.error("Ejemplo: export TELEGRAM_BOT_TOKEN='tu_token_aqui'")
        return

    bot = KubGUAssistantBot(token)
    bot.initialize()

    try:
        logger.info("🤖 Bot iniciado - Escuchando mensajes...")
        logger.info(f"📡 Backend URL: {BACKEND_URL}")
        bot.app.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        logger.info("Bot detenido por usuario")
    except Exception as e:
        logger.error(f"Error en bot: {e}")
    finally:
        asyncio.run(bot.close_http_session())


if __name__ == "__main__":
    main()
