#!/usr/bin/env python3
"""调试 OpenMemory 配置生成过程"""
import sys
import os
import json

sys.path.insert(0, '/usr/src/openmemory')

print("=== Debug OpenMemory Config Generation ===\n")

try:
    from app.utils.memory import get_default_memory_config, _parse_environment_variables
    
    print("Step 1: Get default config")
    config = get_default_memory_config()
    print("Default config (before env parsing):")
    print(json.dumps(config, indent=2))
    
    print("\nStep 2: Parse environment variables")
    config = _parse_environment_variables(config)
    print("Config after env parsing:")
    print(json.dumps(config, indent=2, default=str))
    
    print("\nStep 3: Try to initialize mem0 with this config")
    from mem0 import Memory
    
    try:
        client = Memory.from_config(config)
        print(f"✓ Successfully initialized: {type(client)}")
    except Exception as e:
        import traceback
        print(f"✗ Initialization failed: {type(e).__name__}: {e}")
        traceback.print_exc()
        
except Exception as e:
    import traceback
    print(f"✗ Error: {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.exit(1)
