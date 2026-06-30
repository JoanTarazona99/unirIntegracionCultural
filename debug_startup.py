#!/usr/bin/env python3
"""Debug startup - identify segfault point"""

print("[1] Testing basic imports...")
try:
    import sys
    print(f"  ✓ Python {sys.version}")
except Exception as e:
    print(f"  ✗ {e}")
    exit(1)

print("[2] Testing FastAPI...")
try:
    from fastapi import FastAPI
    print("  ✓ FastAPI OK")
except Exception as e:
    print(f"  ✗ {e}")
    exit(1)

print("[3] Testing Pydantic...")
try:
    from pydantic import BaseModel
    print("  ✓ Pydantic OK")
except Exception as e:
    print(f"  ✗ {e}")
    exit(1)

print("[4] Testing gTTS...")
try:
    from gtts import gTTS
    print("  ✓ gTTS OK")
except Exception as e:
    print(f"  ✗ {e}")

print("[5] Testing SpeechRecognition...")
try:
    import speech_recognition as sr
    print("  ✓ SpeechRecognition OK")
except Exception as e:
    print(f"  ✗ {e}")

print("[6] Testing personalization module...")
try:
    from personalization import get_conversation_memory
    print("  ✓ personalization OK")
except Exception as e:
    print(f"  ✗ {e}")
    exit(1)

print("[7] Testing cache module...")
try:
    from cache_module import get_rag_cache
    print("  ✓ cache_module OK")
except Exception as e:
    print(f"  ✗ {e}")
    exit(1)

print("[8] Testing translator...")
try:
    from translator import create_translator
    print("  ⏳ Loading translator (may take time)...")
    translator = create_translator()
    print("  ✓ translator OK")
except Exception as e:
    print(f"  ✗ {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("[9] Testing enhanced_rag (THIS IS LIKELY THE CULPRIT)...")
try:
    print("  ⏳ Loading EnhancedRAGModule (may take time)...")
    from enhanced_rag import EnhancedRAGModule
    print("  ⏳ Initializing EnhancedRAGModule...")
    rag_module = EnhancedRAGModule()
    print("  ✓ enhanced_rag OK")
except Exception as e:
    print(f"  ✗ {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n✅ All modules loaded successfully!")
