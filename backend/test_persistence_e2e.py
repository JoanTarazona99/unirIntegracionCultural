#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E Tests para la capa de persistencia (Sprint 3)

Valida que los servicios de persistencia funcionen correctamente:
- RedisCacheService (con fallback a LRU)
- DatabaseService (SQLite/PostgreSQL/Memory fallback)

Incluye:
- Happy path tests
- Fallback scenarios (Redis no disponible, DB no disponible)
- Error handling
- Data contract validation
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
from typing import Dict, List
from datetime import datetime

# Import services
from app.services.redis_cache_service import RedisCacheService
from app.services.database_service import DatabaseService
from app.domain.exceptions import ValidationError, AppError


class PersistenceE2ETestRunner:
    """Test runner for persistence layer E2E tests"""
    
    def __init__(self):
        self.test_count = 0
        self.passed = 0
        self.failed = 0
        self.test_results = []
    
    def log(self, msg: str, level: str = "INFO"):
        """Log test message"""
        prefixes = {"INFO": "[TEST]", "OK": "[OK]", "FAIL": "[FAIL]"}
        prefix = prefixes.get(level, "[TEST]")
        print(f"{prefix} {msg}")
    
    def test(self, name: str, condition: bool, expected=None, actual=None) -> bool:
        """Record test result"""
        self.test_count += 1
        if condition:
            self.passed += 1
            self.log(f"[{self.test_count}] {name}... PASS", "OK")
            return True
        else:
            self.failed += 1
            self.log(f"[{self.test_count}] {name}... FAIL", "FAIL")
            if expected is not None and actual is not None:
                self.log(f"    Expected: {expected}", "FAIL")
                self.log(f"    Actual: {actual}", "FAIL")
            return False
    
    def run(self):
        """Run all test suites"""
        print("\n" + "="*80)
        print("E2E TEST SUITE - PERSISTENCE LAYER (Sprint 3)")
        print("="*80)
        
        self.run_redis_cache_tests()
        self.run_database_service_tests()
        
        self.print_summary()
    
    # ==================== RedisCacheService Tests ====================
    
    def run_redis_cache_tests(self):
        """Test RedisCacheService with fallback to LRU"""
        print("\n--- RedisCacheService Tests (with LRU Fallback) ---")
        
        # Test 1: Initialize without Redis (should use LRU fallback)
        try:
            redis_cache = RedisCacheService(redis_client=None)
            self.test(
                "RedisCacheService initialization without Redis",
                redis_cache.using_redis == False
            )
        except Exception as e:
            self.test("RedisCacheService initialization without Redis", False)
        
        # Test 2: Fallback to LRU status
        try:
            status = asyncio.run(redis_cache.get_status())
            self.test(
                "RedisCacheService.get_status shows LRU fallback",
                status.get("backend_type") == "lru"
            )
        except Exception as e:
            self.test("RedisCacheService.get_status shows LRU fallback", False)
        
        # Test 3: Set and get via LRU fallback
        try:
            asyncio.run(redis_cache.set("test_key_1", "test_value_1", ttl=3600))
            result = asyncio.run(redis_cache.get("test_key_1"))
            self.test(
                "RedisCacheService.set/get via LRU fallback",
                result == "test_value_1"
            )
        except Exception as e:
            self.test("RedisCacheService.set/get via LRU fallback", False)
        
        # Test 4: Cache invalidate
        try:
            asyncio.run(redis_cache.set("test_key_2", "test_value_2"))
            asyncio.run(redis_cache.invalidate("test_key_2"))
            result = asyncio.run(redis_cache.get("test_key_2"))
            self.test(
                "RedisCacheService.invalidate removes key",
                result is None
            )
        except Exception as e:
            self.test("RedisCacheService.invalidate removes key", False)
        
        # Test 5: Cache clear
        try:
            asyncio.run(redis_cache.set("key_a", "val_a"))
            asyncio.run(redis_cache.set("key_b", "val_b"))
            cleared = asyncio.run(redis_cache.clear())
            result_a = asyncio.run(redis_cache.get("key_a"))
            result_b = asyncio.run(redis_cache.get("key_b"))
            self.test(
                "RedisCacheService.clear removes all entries",
                result_a is None and result_b is None
            )
        except Exception as e:
            self.test("RedisCacheService.clear removes all entries", False)
        
        # Test 6: Get stats
        try:
            asyncio.run(redis_cache.set("stat_key", {"data": "value"}))
            stats = asyncio.run(redis_cache.get_stats())
            self.test(
                "RedisCacheService.get_stats returns dict",
                isinstance(stats, dict)
            )
        except Exception as e:
            self.test("RedisCacheService.get_stats returns dict", False)
        
        # Test 7: Validation - empty key raises ValidationError
        try:
            asyncio.run(redis_cache.get(""))
            self.test("RedisCacheService validation - empty key", False)
        except ValidationError:
            self.test("RedisCacheService validation - empty key raises ValidationError", True)
        except Exception:
            self.test("RedisCacheService validation - empty key", False)
        
        # Test 8: Validation - negative TTL raises ValidationError
        try:
            asyncio.run(redis_cache.set("key", "value", ttl=-1))
            self.test("RedisCacheService validation - negative TTL", False)
        except ValidationError:
            self.test("RedisCacheService validation - negative TTL raises ValidationError", True)
        except Exception:
            self.test("RedisCacheService validation - negative TTL", False)
    
    # ==================== DatabaseService Tests ====================
    
    def run_database_service_tests(self):
        """Test DatabaseService with SQLite and memory fallback"""
        print("\n--- DatabaseService Tests (SQLite/Memory Fallback) ---")
        
        # Test 1: Initialize database service
        try:
            db_service = DatabaseService(
                database_url="sqlite:///./data/test_assistant.db",
                db_path="./data/test_assistant.db"
            )
            asyncio.run(db_service.initialize())
            self.test(
                "DatabaseService initialization",
                db_service.backend_type in ["sqlite", "memory"]
            )
        except Exception as e:
            self.test("DatabaseService initialization", False)
        
        # Test 2: Save and get message
        try:
            session_id = "test_session_1"
            msg = asyncio.run(db_service.save_message(
                session_id=session_id,
                role="user",
                content="Hola, necesito ayuda",
                language="es"
            ))
            self.test(
                "DatabaseService.save_message returns dict with id",
                msg.get("id") is not None and msg.get("session_id") == session_id
            )
        except Exception as e:
            self.test("DatabaseService.save_message returns dict with id", False)
        
        # Test 3: Get history ordered by timestamp
        try:
            session_id = "test_session_2"
            asyncio.run(db_service.save_message(session_id, "user", "First message", "es"))
            asyncio.run(db_service.save_message(session_id, "assistant", "First response", "es"))
            asyncio.run(db_service.save_message(session_id, "user", "Second message", "es"))
            
            history = asyncio.run(db_service.get_history(session_id, limit=10))
            self.test(
                "DatabaseService.get_history returns list ordered by timestamp",
                len(history) >= 3 and history[0].get("role") == "user"
            )
        except Exception as e:
            self.test("DatabaseService.get_history returns list ordered by timestamp", False)
        
        # Test 4: Save and get profile
        try:
            user_id = "user_test_1"
            profile_data = {
                "country": "Vietnam",
                "visa_type": "student",
                "academic_level": "bachelor",
                "russian_level": "A1"
            }
            saved = asyncio.run(db_service.save_profile(user_id, profile_data))
            self.test(
                "DatabaseService.save_profile returns dict",
                saved.get("user_id") == user_id and saved.get("country") == "Vietnam"
            )
        except Exception as e:
            self.test("DatabaseService.save_profile returns dict", False)
        
        # Test 5: Get profile persists
        try:
            user_id = "user_test_2"
            profile_data = {
                "country": "China",
                "visa_type": "work",
                "academic_level": "master",
                "russian_level": "B1"
            }
            asyncio.run(db_service.save_profile(user_id, profile_data))
            retrieved = asyncio.run(db_service.get_profile(user_id))
            self.test(
                "DatabaseService.get_profile retrieves saved profile",
                retrieved is not None and retrieved.get("russian_level") == "B1"
            )
        except Exception as e:
            self.test("DatabaseService.get_profile retrieves saved profile", False)
        
        # Test 6: Get profile returns None for non-existent user
        try:
            non_existent = asyncio.run(db_service.get_profile("non_existent_user_99999"))
            self.test(
                "DatabaseService.get_profile returns None for missing user",
                non_existent is None
            )
        except Exception as e:
            self.test("DatabaseService.get_profile returns None for missing user", False)
        
        # Test 7: Get status returns dict with backend info
        try:
            status = asyncio.run(db_service.get_status())
            self.test(
                "DatabaseService.get_status dict structure",
                "backend_type" in status and "conversations_count" in status and "profiles_count" in status
            )
        except Exception as e:
            self.test("DatabaseService.get_status dict structure", False)
        
        # Test 8: Validation - empty session_id raises ValidationError
        try:
            asyncio.run(db_service.save_message("", "user", "content"))
            self.test("DatabaseService validation - empty session_id", False)
        except ValidationError:
            self.test("DatabaseService validation - empty session_id raises ValidationError", True)
        except Exception:
            self.test("DatabaseService validation - empty session_id", False)
        
        # Test 9: Validation - invalid role raises ValidationError
        try:
            asyncio.run(db_service.save_message("session", "invalid_role", "content"))
            self.test("DatabaseService validation - invalid role", False)
        except ValidationError:
            self.test("DatabaseService validation - invalid role raises ValidationError", True)
        except Exception:
            self.test("DatabaseService validation - invalid role", False)
        
        # Test 10: Multiple profile updates
        try:
            user_id = "user_test_3"
            asyncio.run(db_service.save_profile(user_id, {"country": "Brazil"}))
            asyncio.run(db_service.save_profile(user_id, {
                "country": "Brazil",
                "visa_type": "student",
                "academic_level": "phd",
                "russian_level": "B2"
            }))
            retrieved = asyncio.run(db_service.get_profile(user_id))
            self.test(
                "DatabaseService multiple profile updates",
                retrieved.get("academic_level") == "phd"
            )
        except Exception as e:
            self.test("DatabaseService multiple profile updates", False)
        
        # Test 11: Get history limit parameter
        try:
            session_id = "test_session_limit"
            for i in range(10):
                asyncio.run(db_service.save_message(
                    session_id, "user", f"Message {i}", "es"
                ))
            
            history_limited = asyncio.run(db_service.get_history(session_id, limit=5))
            self.test(
                "DatabaseService.get_history respects limit parameter",
                len(history_limited) <= 5
            )
        except Exception as e:
            self.test("DatabaseService.get_history respects limit parameter", False)
        
        # Test 12: Backend fallback (memory as default)
        try:
            db_memory = DatabaseService(
                database_url="invalid://connection",
                db_path="/invalid/path/db.db"
            )
            asyncio.run(db_memory.initialize())
            msg = asyncio.run(db_memory.save_message(
                "session_mem", "user", "test", "es"
            ))
            self.test(
                "DatabaseService backend fallback to memory",
                db_memory.backend_type == "memory" and msg.get("id") is not None
            )
        except Exception as e:
            self.test("DatabaseService backend fallback to memory", False)
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("TEST SUMMARY - PERSISTENCE LAYER")
        print("="*80)
        print(f"Total tests: {self.test_count}")
        print(f"Passed: {self.passed} ({100*self.passed//max(self.test_count,1)}%)")
        print(f"Failed: {self.failed}")
        
        if self.failed == 0:
            print("\n" + "="*80)
            print("[OK] ALL PERSISTENCE E2E TESTS PASSED")
            print("="*80)
            return 0
        else:
            print("\n" + "="*80)
            print(f"[FAIL] {self.failed} TEST(S) FAILED")
            print("="*80)
            return 1


if __name__ == "__main__":
    runner = PersistenceE2ETestRunner()
    runner.run()
    exit_code = runner.print_summary()
    sys.exit(exit_code)
