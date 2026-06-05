import sys
import os

print(f"Python: {sys.version}")
print(f"Executable: {sys.executable}")
print(f"Frozen: {getattr(sys, 'frozen', False)}")

try:
    print("\nTrying to import json...")
    import json
    print("SUCCESS: json imported")
    print(f"json module path: {json.__file__}")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\nTrying to import struct...")
    import struct
    print("SUCCESS: struct imported")
except Exception as e:
    print(f"FAILED: {e}")

print("\nTest complete")