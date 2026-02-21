"""
Validation script to check code structure without running full tests.
Run this when dependencies aren't installed.
"""
import sys
from pathlib import Path

def validate_structure():
    """Validate that all expected files exist."""
    base = Path(__file__).parent
    
    required_files = [
        "models.py",
        "scanner.py",
        "main.py",
        "config.yaml",
        "requirements.txt",
        "README.md",
        "sources/__init__.py",
        "sources/base.py",
        "sources/hn_algolia.py",
        "sources/working_nomads.py",
        "sources/aijobs_uk.py",
        "tests/__init__.py",
        "tests/test_models.py",
        "tests/test_scanner.py",
    ]
    
    missing = []
    for file in required_files:
        if not (base / file).exists():
            missing.append(file)
    
    if missing:
        print("❌ Missing files:")
        for f in missing:
            print(f"  - {f}")
        return False
    
    print("✅ All required files present")
    return True


def validate_syntax():
    """Check Python files for syntax errors."""
    import py_compile
    base = Path(__file__).parent
    
    py_files = list(base.glob("*.py")) + list(base.glob("**/*.py"))
    errors = []
    
    for py_file in py_files:
        if "site-packages" in str(py_file) or ".pytest_cache" in str(py_file):
            continue
        try:
            py_compile.compile(py_file, doraise=True)
        except py_compile.PyCompileError as e:
            errors.append((py_file, e))
    
    if errors:
        print("❌ Syntax errors:")
        for file, error in errors:
            print(f"  - {file}: {error}")
        return False
    
    print(f"✅ All {len(py_files)} Python files have valid syntax")
    return True


def main():
    print("=" * 60)
    print("DISC-MVP-1 Validation")
    print("=" * 60)
    
    structure_ok = validate_structure()
    syntax_ok = validate_syntax()
    
    print("=" * 60)
    if structure_ok and syntax_ok:
        print("✅ VALIDATION PASSED")
        print("\nNote: Full pytest tests require:")
        print("  pip install -r requirements.txt")
        print("  pytest discovery/tests/ -v")
        return 0
    else:
        print("❌ VALIDATION FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
