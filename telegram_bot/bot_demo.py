#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEMO DEL BOT DE TELEGRAM
Sistema simulado para testing sin token real
"""

import sys
from pathlib import Path

if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class TelegramBotDemo:
    """Demostración del bot sin conexión real a Telegram"""
    
    def __init__(self):
        self.users = {}
        self.current_user = None
        self.states = {
            'IDLE': 0,
            'SELECTING_COUNTRY': 1,
            'SELECTING_VISA': 2,
            'SELECTING_LEVEL': 3
        }
        self.current_state = self.states['IDLE']
        
        print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║              🤖 BOT DE TELEGRAM - ASISTENTE KUBGU (DEMO)                  ║
║                                                                            ║
║         Simulación del bot sin conexión real a Telegram                   ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
        """)
    
    def print_menu(self):
        print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                           MENÚ PRINCIPAL                                  ║
╚════════════════════════════════════════════════════════════════════════════╝

Comandos Disponibles:
  /start      - Iniciar bot y recibir bienvenida
  /setup      - Configurar tu perfil
  /search     - Buscar en documentos
  /phrases    - Ver frases útiles
  /profile    - Ver tu perfil
  /help       - Ayuda de comandos
  /quit       - Salir del bot

O escribe tu pregunta directamente para buscar información.
        """)
    
    def cmd_start(self):
        """Comando /start"""
        print("""
✅ ¡Bienvenido al Asistente Inteligente de Integración Cultural!

Soy tu asistente para estudiantes extranjeros en la Universidad Estatal de Kubán.

Puedo ayudarte con:
  • Información de registro y migración
  • Documentos requeridos
  • Visas y permisos
  • Información del dormitorio
  • Asuntos académicos
  • Comunicación en ruso

Escribe /setup para comenzar tu configuración personal.
        """)
    
    def cmd_setup(self):
        """Comando /setup para configurar perfil"""
        print("\n📋 Configuración de Perfil Personalizado\n")
        
        # País
        print("🌍 Selecciona tu país:")
        print("  1. Vietnam")
        print("  2. China")
        print("  3. Otros")
        country_opt = input("Opción (1-3): ").strip()
        countries = {'1': 'Vietnam', '2': 'China', '3': 'Otros'}
        country = countries.get(country_opt, 'Vietnam')
        print(f"✅ País seleccionado: {country}")
        
        # Tipo de visa
        print("\n📄 Tipo de visa:")
        print("  1. Student")
        print("  2. Work")
        print("  3. Study Visit")
        visa_opt = input("Opción (1-3): ").strip()
        visas = {'1': 'student', '2': 'work', '3': 'study_visit'}
        visa = visas.get(visa_opt, 'student')
        print(f"✅ Visa seleccionada: {visa}")
        
        # Nivel de ruso
        print("\n🗣️ Nivel de ruso (MCER):")
        print("  1. A1 (Principiante)")
        print("  2. A2 (Elemental)")
        print("  3. B1 (Intermedio)")
        print("  4. B2 (Intermedio-Alto)")
        print("  5. C1 (Avanzado)")
        level_opt = input("Opción (1-5): ").strip()
        levels = {'1': 'A1', '2': 'A2', '3': 'B1', '4': 'B2', '5': 'C1'}
        level = levels.get(level_opt, 'A1')
        print(f"✅ Nivel de ruso seleccionado: {level}")
        
        # Guardar perfil
        user_id = "demo_user_001"
        self.users[user_id] = {
            'country': country,
            'visa': visa,
            'russian_level': level
        }
        self.current_user = user_id
        
        print(f"""
✅ Perfil creado exitosamente:
   País: {country}
   Visa: {visa}
   Nivel Ruso: {level}

Tu perfil se ha guardado y será usado para personalizaciones.
        """)
    
    def cmd_search(self):
        """Comando /search"""
        print("\n🔍 Búsqueda en Documentos Oficiales\n")
        query = input("¿Qué información buscas? → ").strip()
        
        if not query:
            print("❌ Por favor escribe una pregunta.")
            return
        
        # Respuestas simuladas
        responses = {
            'visa': """
📄 INFORMACIÓN SOBRE VISAS (МВД РФ)

Una visa de estudiante es requerida para estudios en Rusia.
Proceso:
1. Obtener carta de invitación de КубГУ
2. Presentar solicitud en embajada rusa
3. Pago de arancel de visa
4. Registro en МВД РФ tras llegada

Tiempo aproximado: 2-4 semanas

Fuente: МВД РФ (Ministerio del Interior)
            """,
            'registro': """
📋 REGISTRO EN МФЦ (Centro Multifuncional)

Pasos para registrarse:
1. Completar formulario de registro
2. Presentar pasaporte y visa
3. Comprobante de domicilio (carta de КубГУ)
4. Pago de aranceles (si aplica)
5. Foto (4x6 cm)

Ubicación МФЦ en Krasnodar: Calle Krasnaya 122

Horario: Lunes-Viernes 9:00-18:00

Fuente: МФЦ (Centro Multifuncional)
            """,
            'dormitorio': """
🏢 INFORMACIÓN DE DORMITORIO (КубГУ)

Alojamiento disponible:
• Dormitorios para estudiantes del 1er año
• Cuartos compartidos (2-3 personas)
• Servicios incluidos: agua, electricidad, WiFi
• Comedor en campus
• Biblioteca 24/7

Solicitud: Contacta a oficina de estudiantes extranjeros
Email: international@kubsu.ru

Costo: 1,500-2,000 rubles/mes

Fuente: КубГУ (Universidad Estatal de Kubán)
            """,
            'seguro': """
🏥 SEGUROS MEDICOS (МФЦ)

Seguro médico requerido para estudiantes:
• Cobertura completa: ~3,000 rubles/año
• Cubre medicina general y emergencias
• Válido en hospitales públicos rusos

Proveedores:
- ИНГОССТРАХ
- АЛЬФА СТРАХОВКА
- Otros aprobados

Documentos necesarios:
- Pasaporte
- Visa
- Registro temporal

Fuente: МФЦ (Centro Multifuncional)
            """
        }
        
        # Buscar respuesta relevante
        query_lower = query.lower()
        matched = False
        
        for key, response in responses.items():
            if key in query_lower:
                print(response)
                matched = True
                break
        
        if not matched:
            print(f"""
❓ BÚSQUEDA: "{query}"

No encontré información específica, pero aquí hay recursos útiles:

📞 Contactos importantes:
• Oficina de Estudiantes Extranjeros (КубГУ): +7-861-220-30-00
• Consulado: +7-861-210-36-36
• МФЦ: +7-861-212-00-69
• Línea de emergencia: 112

🌐 Portales útiles:
• Госуслуги: https://www.gosuslugi.ru
• КубГУ: https://www.kubsu.ru
• МВД РФ: https://www.mvd.ru
            """)
    
    def cmd_phrases(self):
        """Comando /phrases - Frases útiles"""
        print("""
💬 FRASES ÚTILES EN RUSO

Registro y Migración:
  Где находится МФЦ? - ¿Dónde está el МFC?
  Мне нужна виза - Necesito una visa
  Как зарегистрироваться? - ¿Cómo registrarse?

Medicina:
  Мне нужен врач - Necesito un doctor
  Медицинское страхование - Seguro médico
  Где больница? - ¿Dónde está el hospital?

Dormitorio:
  Общежитие - Dormitorio
  Комната - Cuarto
  Сосед - Compañero de cuarto

Académico:
  Начало занятий - Comienzo de clases
  Экзамен - Examen
  Библиотека - Biblioteca

Comunicación:
  Привет - Hola
  Спасибо - Gracias
  Пожалуйста - Por favor
        """)
    
    def cmd_profile(self):
        """Comando /profile"""
        if self.current_user and self.current_user in self.users:
            profile = self.users[self.current_user]
            print(f"""
👤 TU PERFIL PERSONALIZADO

País: {profile['country']}
Tipo de Visa: {profile['visa']}
Nivel de Ruso: {profile['russian_level']}

Personalizaciones:
✓ Frecuencia recomendada de frases: diaria
✓ Nivel de complejidad: Simplificado ({profile['russian_level']})
✓ Contextos prioritarios: admin, practical, medical
            """)
        else:
            print("❌ No tienes un perfil configurado. Usa /setup para crear uno.")
    
    def cmd_help(self):
        """Comando /help"""
        print("""
📖 AYUDA Y COMANDOS

Comandos Principales:
  /start      Iniciar y recibir bienvenida
  /setup      Configurar perfil personalizado
  /search     Buscar en documentos oficiales
  /phrases    Ver frases útiles en ruso
  /profile    Ver tu perfil personalizado
  /help       Mostrar esta ayuda
  /quit       Salir del bot

Ejemplos de Búsqueda:
  /search visa
  /search registro
  /search dormitorio
  /search seguro
  /search academia

O simplemente escribe tu pregunta:
  "¿Cómo registro?" → el bot buscará en la base de conocimientos
  "Necesito seguro médico" → respuesta personalizada
        """)
    
    def run(self):
        """Ejecutar loop interactivo del bot"""
        self.print_menu()
        
        while True:
            try:
                user_input = input("\n➜ Bot >> ").strip()
                
                if not user_input:
                    continue
                
                # Procesar comandos
                if user_input == "/start":
                    self.cmd_start()
                elif user_input == "/setup":
                    self.cmd_setup()
                elif user_input == "/search":
                    self.cmd_search()
                elif user_input == "/phrases":
                    self.cmd_phrases()
                elif user_input == "/profile":
                    self.cmd_profile()
                elif user_input == "/help":
                    self.cmd_help()
                elif user_input == "/quit" or user_input == "/exit":
                    print("\n👋 ¡Hasta luego! Gracias por usar el Asistente de КубГУ.\n")
                    break
                elif user_input.startswith("/"):
                    print(f"❓ Comando desconocido: {user_input}")
                    print("   Escribe /help para ver comandos disponibles")
                else:
                    # Búsqueda general
                    print("\n🔍 Buscando información...")
                    # Simular búsqueda
                    if 'visa' in user_input.lower():
                        self.cmd_search()
                    else:
                        print(f"Pregunta recibida: '{user_input}'")
                        print("Respuesta (desde documentos oficiales):")
                        print("  La información se buscaría en la base de datos RAG...")
            
            except KeyboardInterrupt:
                print("\n\n👋 Bot detenido por usuario.\n")
                break
            except Exception as e:
                print(f"❌ Error: {e}")


def main():
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║         🚀 DEMO INTERACTIVO DEL BOT DE TELEGRAM - ASISTENTE KUBGU        ║
║                                                                            ║
║  Este es un simulador del bot sin necesidad de token real de Telegram.    ║
║  Puedes probar todos los comandos y el flujo de conversación.             ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    bot = TelegramBotDemo()
    bot.run()


if __name__ == "__main__":
    main()
