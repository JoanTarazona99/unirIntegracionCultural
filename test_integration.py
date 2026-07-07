#!/usr/bin/env python3
"""
Test Knowledge Integration System
Verifies that web sources are automatically integrated into the KB
"""

import sys
import os
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from knowledge_integrator import KnowledgeIntegrator

def test_integration():
    """Run integration tests"""
    
    print("\n" + "="*80)
    print("📚 KNOWLEDGE INTEGRATION SYSTEM - TEST")
    print("="*80)
    
    # Initialize integrator
    integrator = KnowledgeIntegrator()
    
    # 1. Check current status
    print("\n1️⃣ INTEGRATION STATUS")
    print("-" * 80)
    status = integrator.get_integration_status()
    print(f"   Total acquisitions: {status['total_acquisitions']}")
    print(f"   Successful acquisitions: {status['successful_acquisitions']}")
    print(f"   Already integrated: {status['integrated_count']}")
    print(f"   Pending: {status['pending_count']}")
    
    # 2. Show pending queries
    if status['pending_count'] > 0:
        print(f"\n2️⃣ PENDING QUERIES ({status['pending_count']})")
        print("-" * 80)
        for i, query in enumerate(status['pending_queries'], 1):
            print(f"   {i}. {query}")
        
        # 3. Run integration
        print(f"\n3️⃣ RUNNING INTEGRATION")
        print("-" * 80)
        print(f"   Processing {status['pending_count']} pending acquisitions...")
        
        result = integrator.integrate_pending(auto_add=True)
        
        print(f"\n   ✅ Integration Complete:")
        print(f"      - Integrated: {result['integrated_count']}")
        print(f"      - Failed: {result['failed_count']}")
        
        if result['integrated']:
            print(f"\n   📝 Successfully integrated sections:")
            for entry in result['integrated']:
                print(f"      ✓ {entry['section_name']}")
                print(f"        Query: {entry['query']}")
                print(f"        Source: {entry['source_url']}")
        
        if result['failed']:
            print(f"\n   ❌ Failed integrations:")
            for entry in result['failed']:
                print(f"      ✗ {entry.get('query')}")
                if 'error' in entry:
                    print(f"        Error: {entry['error']}")
                elif 'reason' in entry:
                    print(f"        Reason: {entry['reason']}")
    
    else:
        print("\n   ✨ No pending acquisitions - KB is up to date!")
    
    # 4. Summary
    print(f"\n4️⃣ FINAL STATUS")
    print("-" * 80)
    final_status = integrator.get_integration_status()
    print(f"   Total acquisitions: {final_status['total_acquisitions']}")
    print(f"   Integrated: {final_status['integrated_count']}")
    print(f"   Remaining pending: {final_status['pending_count']}")
    
    # 5. Check integration_log.json
    print(f"\n5️⃣ INTEGRATION LOG")
    print("-" * 80)
    integ_log = integrator.load_integration_log()
    if integ_log:
        print(f"   Total entries in integration_log.json: {len(integ_log)}")
        for entry in integ_log[-3:]:  # Show last 3
            print(f"   - {entry['section_name']} ({entry['timestamp']})")
    else:
        print(f"   No entries in integration_log.json yet")
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETE")
    print("="*80 + "\n")
    
    return final_status['pending_count'] == 0


if __name__ == '__main__':
    success = test_integration()
    sys.exit(0 if success else 1)
