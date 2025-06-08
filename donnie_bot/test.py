try:
    import PyPDF2
    print("✅ PyPDF2 imported successfully")
except ImportError as e:
    print(f"❌ PyPDF2 failed: {e}")

try:
    import fitz  # PyMuPDF
    print("✅ PyMuPDF (fitz) imported successfully")
except ImportError as e:
    print(f"❌ PyMuPDF failed: {e}")

try:
    from PIL import Image
    print("✅ Pillow imported successfully")
except ImportError as e:
    print(f"❌ Pillow failed: {e}")