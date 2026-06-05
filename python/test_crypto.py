import sys
print(f"Python version: {sys.version}")
print(f"sys.path: {sys.path}")

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    print("SUCCESS: AESGCM imported successfully")
except ImportError as e:
    print(f"ERROR: Failed to import AESGCM: {e}")
    
try:
    import cryptography
    print(f"cryptography version: {cryptography.__version__}")
    print(f"cryptography path: {cryptography.__file__}")
except Exception as e:
    print(f"ERROR: {e}")
