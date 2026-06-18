import logging
import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# Cargar variables de entorno desde .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Estados para conversación
SELECTING_COUNTRY, SELECTING_VISA, SELECTING_LEVEL = range(3)

class KubGUAssistantBot:
    """Bot de Telegram para Asistente de Integración Cultural"""
    
    def __init__(self, token: str):
        self.token = token
        self.app = None
        self.user_profiles = {}
    
    def initialize(self):
        """Inicializar la aplicación del bot"""
        self.app = Application.builder().token(self.token).build()
        
        # Handlers de comandos
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("profile", self.profile_command))
        self.app.add_handler(CommandHandler("phrases", self.phrases_command))
        self.app.add_handler(CommandHandler("search", self.search_command))
        
        # Handler de mensajes generales
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Conversation handler para setup
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("setup", self.setup_start)],
            states={
                SELECTING_COUNTRY: [MessageHandler(filters.TEXT, self.select_country)],
                SELECTING_VISA: [MessageHandler(filters.TEXT, self.select_visa)],
                SELECTING_LEVEL: [MessageHandler(filters.TEXT, self.select_level)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        self.app.add_handler(conv_handler)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        user_id = update.message.from_user.id
        user_name = update.message.from_user.first_name
        
        welcome_text = f"""
        ¡Hola {user_name}! 👋
        
        Soy el Asistente Inteligente de Integración Cultural de KubGU.
        
        Estoy aquí para ayudarte con:
        • Frases útiles en ruso
        • Procedimientos administrativos
        • Información sobre la universidad
        • Consejos culturales
        
        Usa /help para ver todos los comandos disponibles.
        Usa /setup para empezar la configuración personalizada.
        """
        
        await update.message.reply_text(welcome_text)
        logger.info(f"Usuario {user_id} inició sesión")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help"""
        help_text = """
        *Comandos disponibles:*
        
        /start - Ver mensaje de bienvenida
        /setup - Configurar perfil personalizado
        /profile - Ver tu perfil actual
        /phrases - Ver frases útiles
        /search [texto] - Buscar información
        /help - Este mensaje
        
        *Puedes escribir preguntas naturales:*
        - "¿Dónde está el МФЦ?"
        - "¿Cómo registrarse en el dormitorio?"
        - "Necesito ayuda con documentos"
        """
        
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def setup_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Iniciar configuración de perfil"""
        user_id = update.message.from_user.id
        
        keyboard = [
            [InlineKeyboardButton("Vietnam", callback_data="country_vietnam")],
            [InlineKeyboardButton("China", callback_data="country_china")],
            [InlineKeyboardButton("Kazakhstan", callback_data="country_kazakhstan")],
            [InlineKeyboardButton("Armenia", callback_data="country_armenia")],
            [InlineKeyboardButton("Otro", callback_data="country_other")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "¿De qué país eres?",
            reply_markup=reply_markup
        )
        
        return SELECTING_COUNTRY
    
    async def select_country(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Seleccionar país"""
        user_id = update.message.from_user.id
        country = update.message.text
        
        self.user_profiles[user_id] = {"country": country}
        
        keyboard = [
            [InlineKeyboardButton("Estudiante", callback_data="visa_student")],
            [InlineKeyboardButton("Intercambio", callback_data="visa_exchange")],
            [InlineKeyboardButton("Visitante", callback_data="visa_visit")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "¿Qué tipo de visa tienes?",
            reply_markup=reply_markup
        )
        
        return SELECTING_VISA
    
    async def select_visa(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Seleccionar tipo de visa"""
        user_id = update.message.from_user.id
        visa_type = update.message.text
        
        self.user_profiles[user_id]["visa_type"] = visa_type
        
        keyboard = [
            [InlineKeyboardButton("A1-A2", callback_data="level_a2")],
            [InlineKeyboardButton("B1", callback_data="level_b1")],
            [InlineKeyboardButton("B2", callback_data="level_b2")],
            [InlineKeyboardButton("C1+", callback_data="level_c1")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "¿Cuál es tu nivel de ruso?",
            reply_markup=reply_markup
        )
        
        return SELECTING_LEVEL
    
    async def select_level(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Seleccionar nivel de ruso"""
        user_id = update.message.from_user.id
        level = update.message.text
        
        self.user_profiles[user_id]["russian_level"] = level
        
        profile = self.user_profiles[user_id]
        confirmation = f"""
        ¡Perfil creado! ✅
        
        País: {profile.get("country")}
        Visa: {profile.get("visa_type")}
        Nivel de ruso: {profile.get("russian_level")}
        
        Ahora puedo darte recomendaciones personalizadas.
        Escribe /phrases para ver frases útiles.
        """
        
        await update.message.reply_text(confirmation)
        logger.info(f"Perfil creado para usuario {user_id}: {profile}")
        
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancelar configuración"""
        await update.message.reply_text("Configuración cancelada.")
        return ConversationHandler.END
    
    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ver perfil actual"""
        user_id = update.message.from_user.id
        
        if user_id in self.user_profiles:
            profile = self.user_profiles[user_id]
            text = f"""
            *Tu Perfil:*
            
            País: {profile.get("country", "No configurado")}
            Visa: {profile.get("visa_type", "No configurado")}
            Nivel de ruso: {profile.get("russian_level", "No configurado")}
            """
            await update.message.reply_text(text, parse_mode="Markdown")
        else:
            await update.message.reply_text(
                "No tienes perfil configurado. Usa /setup para crear uno."
            )
    
    async def phrases_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ver frases útiles"""
        phrases = [
            "🇷🇺 *Frases útiles:*",
            "",
            "1. Мне нужна помощь (Mne nuzhna pomoshch') - Necesito ayuda",
            "2. Где находится...? (Gde nakhoditsya...?) - ¿Dónde está...?",
            "3. Говорите медленнее (Govorite medlennee) - Habla más lentamente",
            "4. Не понимаю (Ne ponimayu) - No entiendo",
            "5. Спасибо (Spasibo) - Gracias",
        ]
        
        await update.message.reply_text("\n".join(phrases), parse_mode="Markdown")
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Buscar información"""
        if not context.args:
            await update.message.reply_text("Uso: /search [término]")
            return
        
        query = " ".join(context.args)
        
        # Aquí integrar búsqueda RAG
        response = f"Buscando información sobre: *{query}*\n\n[Búsqueda RAG en construcción]"
        
        await update.message.reply_text(response, parse_mode="Markdown")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar mensajes generales"""
        user_message = update.message.text
        user_id = update.message.from_user.id
        
        logger.info(f"Mensaje de {user_id}: {user_message}")
        
        # Respuestas simples
        if "хелп" in user_message.lower() or "ayuda" in user_message.lower():
            await update.message.reply_text("Usa /help para ver los comandos disponibles.")
        elif "привет" in user_message.lower() or "hola" in user_message.lower():
            await update.message.reply_text("¡Привет! (¡Hola!) ¿Cómo te puedo ayudar?")
        else:
            # Respuesta genérica
            await update.message.reply_text(
                "Entiendo que preguntas sobre: " + user_message + "\n\n"
                "Estoy procesando tu pregunta...\n"
                "[Integración con RAG en construcción]"
            )
    
def main():
    """Función principal"""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    
    if token == "YOUR_BOT_TOKEN_HERE":
        logger.error("Configura TELEGRAM_BOT_TOKEN en variables de entorno")
        return
    
    bot = KubGUAssistantBot(token)
    bot.initialize()
    
    try:
        logger.info("🤖 Bot iniciado - Escuchando mensajes...")
        bot.app.run_polling()
    except KeyboardInterrupt:
        logger.info("Bot detenido por usuario")
    except Exception as e:
        logger.error(f"Error en bot: {e}")

if __name__ == "__main__":
    main()
