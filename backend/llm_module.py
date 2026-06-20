"""
LLM Module - Local LLM integration with Ollama
Supports: llama3, qwen2, mistral, and other Ollama models
Falls back to template responses if Ollama is not available
"""

import os
import json
import asyncio
from typing import List, Dict, Optional, Generator, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime

# Try to import ollama
OLLAMA_AVAILABLE = False
try:
    import ollama
    OLLAMA_AVAILABLE = True
    print("[LLM] ollama library loaded - Local LLM enabled")
except ImportError:
    print("[LLM] ollama not available - Using template fallback")

# Try to import httpx for async operations
HTTPX_AVAILABLE = False
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    print("[LLM] httpx not available - Async generation limited")


@dataclass
class Message:
    """Chat message structure"""
    role: str  # 'system', 'user', 'assistant'
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ConversationSession:
    """Conversation session with history"""
    session_id: str
    messages: List[Message] = field(default_factory=list)
    max_history: int = 10
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_message(self, role: str, content: str):
        """Add message to conversation history"""
        self.messages.append(Message(role=role, content=content))
        # Keep only last N messages
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]

    def get_history(self) -> List[Dict]:
        """Get conversation history as list of dicts"""
        return [{"role": m.role, "content": m.content} for m in self.messages]

    def clear_history(self):
        """Clear conversation history"""
        self.messages = []


class LLMModule:
    """
    LLM Module with Ollama support and template fallback

    Features:
    - Local LLM via Ollama (llama3, qwen2, mistral)
    - Template fallback when LLM unavailable
    - Conversation history management
    - Streaming response support
    """

    SUPPORTED_MODELS = [
        'llama3',
        'llama3.1',
        'llama3.2',
        'qwen2',
        'qwen2.5',
        'mistral',
        'mistral-nemo',
        'gemma2',
        'phi3',
        'codellama'
    ]

    # System prompt for the KubGU assistant
    DEFAULT_SYSTEM_PROMPT = """Ты - полезный ассистент для иностранных студентов Кубанского государственного университета (КубГУ).

Твоя задача:
- Помогать студентам с вопросами о регистрации, визах, общежитии, учебе
- Отвечать на русском языке (или на языке запроса)
- Быть дружелюбным и информативным
- Использовать предоставленный контекст документов для точных ответов

Если информации нет в контексте, честно скажи об этом и предложи обратиться в администрацию."""

    def __init__(
        self,
        model: str = 'llama3',
        host: str = None,
        system_prompt: str = None
    ):
        self.model = model
        self.host = host or os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.sessions: Dict[str, ConversationSession] = {}
        self._initialized = False
        self._available_models = []

        if OLLAMA_AVAILABLE:
            self._check_availability()

    def _check_availability(self) -> bool:
        """Check if Ollama server is running and model is available"""
        try:
            # List available models
            models_response = ollama.list()
            if models_response and 'models' in models_response:
                self._available_models = [m['model'] for m in models_response['models']]
                print(f"[LLM] Available Ollama models: {self._available_models}")

                # Check if requested model is available
                if self.model in self._available_models or any(self.model in m for m in self._available_models):
                    self._initialized = True
                    print(f"[LLM] Model '{self.model}' available - LLM mode activated")
                else:
                    print(f"[LLM] Model '{self.model}' not found. Available: {self._available_models}")
                    print(f"[LLM] Pull model with: ollama pull {self.model}")
            return self._initialized
        except Exception as e:
            print(f"[LLM] Ollama check failed: {e}")
            return False

    def is_available(self) -> bool:
        """Check if LLM is available"""
        return self._initialized and OLLAMA_AVAILABLE

    def get_status(self) -> Dict:
        """Get LLM module status"""
        return {
            "available": self.is_available(),
            "model": self.model,
            "host": self.host,
            "available_models": self._available_models,
            "fallback_mode": not self.is_available()
        }

    # ==================== Session Management ====================

    def get_or_create_session(self, session_id: str) -> ConversationSession:
        """Get or create conversation session"""
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationSession(session_id=session_id)
        return self.sessions[session_id]

    def add_message(self, session_id: str, role: str, content: str):
        """Add message to session history"""
        session = self.get_or_create_session(session_id)
        session.add_message(role, content)

    def get_history(self, session_id: str) -> List[Dict]:
        """Get conversation history for session"""
        session = self.get_or_create_session(session_id)
        return session.get_history()

    def clear_session(self, session_id: str):
        """Clear conversation history for session"""
        if session_id in self.sessions:
            self.sessions[session_id].clear_history()

    # ==================== Response Generation ====================

    def generate_response(
        self,
        query: str,
        context_docs: List[Dict],
        language: str = 'ru',
        session_id: str = None
    ) -> str:
        """
        Generate response using LLM or template fallback

        Args:
            query: User query
            context_docs: Retrieved documents from RAG
            language: Response language ('ru', 'es', 'en')
            session_id: Optional session ID for conversation history

        Returns:
            Generated response string
        """
        if self.is_available():
            return self._generate_with_llm(query, context_docs, language, session_id)
        else:
            return self._generate_template_response(query, context_docs, language)

    def _generate_with_llm(
        self,
        query: str,
        context_docs: List[Dict],
        language: str,
        session_id: str = None
    ) -> str:
        """Generate response using Ollama LLM"""
        try:
            # Build context from documents
            context_text = self._build_context(context_docs)

            # Translate context if not Russian
            if language != 'ru' and context_text:
                try:
                    from translator import MultiLanguageTranslator
                    translator = MultiLanguageTranslator()
                    if translator.has_translator:
                        context_text = translator.translate_text(context_text, language)
                except Exception as e:
                    print(f"[LLM] Context translation failed: {e}")

            # Language instruction
            lang_instruction = {
                'ru': 'Отвечай на русском языке.',
                'es': 'Responde en español.',
                'en': 'Respond in English.',
                'fr': 'Répondez en français.',
                'de': 'Antworten Sie auf Deutsch.'
            }.get(language, 'Respond in the language of the query.')

            # Build messages
            messages = [
                {"role": "system", "content": f"{self.system_prompt}\n\n{lang_instruction}"},
            ]

            # Add conversation history if session provided
            if session_id:
                history = self.get_history(session_id)
                messages.extend(history)

            # Add current query with context
            query_label = {
                'ru': 'Вопрос',
                'es': 'Pregunta',
                'en': 'Question',
                'fr': 'Question'
            }.get(language, 'Question')

            context_label = {
                'ru': 'Контекст документов',
                'es': 'Contexto de documentos',
                'en': 'Document context',
                'fr': 'Contexte des documents'
            }.get(language, 'Document context')

            user_message = f"{query_label}: {query}\n\n{context_label}:\n{context_text}" if context_text else query
            messages.append({"role": "user", "content": user_message})

            # Call Ollama
            response = ollama.chat(
                model=self.model,
                messages=messages
            )

            # Extract response
            assistant_response = response['message']['content']

            # Update conversation history
            if session_id:
                self.add_message(session_id, 'user', query)
                self.add_message(session_id, 'assistant', assistant_response)

            return assistant_response

        except Exception as e:
            print(f"[LLM] Generation error: {e}")
            return self._generate_template_response(query, context_docs, language)

    def _generate_template_response(
        self,
        query: str,
        context_docs: List[Dict],
        language: str
    ) -> str:
        """Fallback template-based response"""
        if not context_docs:
            return self._no_context_response(query, language)

        best_match = context_docs[0]
        content = best_match.get('content', '')
        source = best_match.get('source', 'KubGU')
        source_url = best_match.get('source_url', 'https://kubsu.ru')

        # Translate content if language is not Russian and translator is available
        if language != 'ru' and content:
            try:
                from translator import MultiLanguageTranslator
                translator = MultiLanguageTranslator()
                if translator.has_translator:
                    content = translator.translate_text(content, language)
            except Exception as e:
                print(f"[LLM] Translation failed: {e}, using original content")

        # Language-specific templates
        if language == 'ru' or not language:
            return f"""📌 ОФИЦИАЛЬНАЯ ИНФОРМАЦИЯ: {query}

📄 Источник: {source}

{content}

🔗 Подробнее: {source_url}"""

        elif language == 'es':
            return f"""📌 INFORMACIÓN OFICIAL: {query}

📄 Fuente: {source}

{content}

🔗 Más información: {source_url}"""

        elif language == 'fr':
            return f"""📌 INFORMATION OFFICIELLE: {query}

📄 Source: {source}

{content}

🔗 Plus d'infos: {source_url}"""

        else:  # English
            return f"""📌 OFFICIAL INFORMATION: {query}

📄 Source: {source}

{content}

🔗 More info: {source_url}"""

    def _no_context_response(self, query: str, language: str) -> str:
        """Response when no context found"""
        responses = {
            'ru': f"К сожалению, я не нашел информацию по запросу '{query}'. Обратитесь в администрацию КубГУ: +7-861-XXX-XXXX или посетите https://kubsu.ru",
            'es': f"No encontré información sobre '{query}'. Contacte a la administración de KubGU: +7-861-XXX-XXXX o visite https://kubsu.ru",
            'en': f"Sorry, I couldn't find information about '{query}'. Contact KubGU administration: +7-861-XXX-XXXX or visit https://kubsu.ru",
            'fr': f"Désolé, je n'ai pas trouvé d'informations sur '{query}'. Contactez l'administration de KubGU: +7-861-XXX-XXXX ou visitez https://kubsu.ru"
        }
        return responses.get(language, responses['en'])

    def _build_context(self, context_docs: List[Dict]) -> str:
        """Build context string from documents"""
        if not context_docs:
            return ""

        context_parts = []
        for i, doc in enumerate(context_docs[:3], 1):
            source = doc.get('source', 'Unknown')
            title = doc.get('title', 'Untitled')
            content = doc.get('content', '')[:500]  # Limit content length
            context_parts.append(f"[{i}] {source} - {title}:\n{content}")

        return "\n\n".join(context_parts)

    # ==================== Streaming Generation ====================

    def generate_stream(
        self,
        query: str,
        context_docs: List[Dict],
        language: str = 'ru',
        session_id: str = None
    ) -> Generator[str, None, None]:
        """
        Generate response as a stream of tokens

        Yields:
            Tokens/chunks of the response
        """
        if not self.is_available():
            # Yield complete template response
            yield self._generate_template_response(query, context_docs, language)
            return

        try:
            # Build context
            context_text = self._build_context(context_docs)

            # Build messages
            messages = [
                {"role": "system", "content": self.system_prompt},
            ]

            if session_id:
                messages.extend(self.get_history(session_id))

            user_message = f"Вопрос: {query}\n\nКонтекст:\n{context_text}" if context_text else query
            messages.append({"role": "user", "content": user_message})

            # Stream from Ollama
            full_response = ""
            for chunk in ollama.chat(
                model=self.model,
                messages=messages,
                stream=True
            ):
                if chunk and 'message' in chunk and 'content' in chunk['message']:
                    token = chunk['message']['content']
                    full_response += token
                    yield token

            # Update history after complete
            if session_id:
                self.add_message(session_id, 'user', query)
                self.add_message(session_id, 'assistant', full_response)

        except Exception as e:
            print(f"[LLM] Stream error: {e}")
            yield self._generate_template_response(query, context_docs, language)

    async def generate_stream_async(
        self,
        query: str,
        context_docs: List[Dict],
        language: str = 'ru',
        session_id: str = None
    ) -> AsyncGenerator[str, None]:
        """
        Async streaming generation using httpx

        For use with FastAPI StreamingResponse
        """
        if not HTTPX_AVAILABLE or not self.is_available():
            yield self._generate_template_response(query, context_docs, language)
            return

        try:
            context_text = self._build_context(context_docs)

            messages = [{"role": "system", "content": self.system_prompt}]

            if session_id:
                messages.extend(self.get_history(session_id))

            user_message = f"Вопрос: {query}\n\nКонтекст:\n{context_text}" if context_text else query
            messages.append({"role": "user", "content": user_message})

            # Async HTTP call to Ollama
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    'POST',
                    f"{self.host}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": True
                    }
                ) as response:
                    full_response = ""
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if 'message' in data and 'content' in data['message']:
                                    token = data['message']['content']
                                    full_response += token
                                    yield token
                            except json.JSONDecodeError:
                                continue

                    # Update history
                    if session_id:
                        self.add_message(session_id, 'user', query)
                        self.add_message(session_id, 'assistant', full_response)

        except Exception as e:
            print(f"[LLM] Async stream error: {e}")
            yield self._generate_template_response(query, context_docs, language)


def create_llm(model: str = 'llama3') -> LLMModule:
    """Factory function to create LLM module"""
    return LLMModule(model=model)


# Singleton instance
_llm_instance: Optional[LLMModule] = None


def get_llm_instance(model: str = 'llama3') -> LLMModule:
    """Get or create singleton LLM instance"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMModule(model=model)
    return _llm_instance


if __name__ == "__main__":
    # Test LLM module
    llm = create_llm()

    print("\n" + "="*60)
    print("LLM MODULE TEST")
    print("="*60)

    print(f"\nStatus: {llm.get_status()}")

    # Test with mock documents
    test_docs = [
        {
            'source': 'КубГУ',
            'title': 'Регистрация',
            'content': 'Иностранные студенты должны зарегистрироваться в течение 7 дней.',
            'source_url': 'https://kubsu.ru'
        }
    ]

    print("\nTest query: 'Как зарегистрироваться?'")
    response = llm.generate_response(
        "Как зарегистрироваться?",
        test_docs,
        language='ru'
    )
    print(f"\nResponse:\n{response}")
