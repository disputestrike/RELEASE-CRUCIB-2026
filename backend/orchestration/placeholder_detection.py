"""
placeholder_detection.py — Detect placeholder/stub/mock output in generated files.
"""

import re
from typing import Optional


def contains_placeholder(content: str) -> bool:
    """
    Detect if content contains placeholder, stub, or mock output.
    Returns True if placeholders are detected, False otherwise.
    """
    if not content:
        return False
    
    # List of common placeholder patterns
    placeholder_patterns = [
        r"TODO\s*[:;]?",
        r"FIXME\s*[:;]?",
        r"PLACEHOLDER",
        r"STUB",
        r"MOCK",
        r"XXX\s*[:;]?",
        r"HACK\s*[:;]?",
        r"TEMP\s*[:;]?",
        r"TEMPORARY",
        r"EXAMPLE\s*[:;]?",
        r"DEMO\s*[:;]?",
        r"DUMMY",
        r"FAKE",
        r"REPLACE_ME",
        r"CHANGE_ME",
        r"UPDATE_ME",
        r"IMPLEMENT_ME",
        r"FILL_IN",
        r"\.\.\..*\(placeholder\)",
        r"pass\s*#\s*placeholder",
        r"return\s+None\s*#\s*placeholder",
        r"raise\s+NotImplementedError",
        r"raise\s+Exception\s*\(\s*['\"].*placeholder",
    ]
    
    # Convert to lowercase for case-insensitive matching
    content_lower = content.lower()
    
    for pattern in placeholder_patterns:
        if re.search(pattern, content_lower, re.IGNORECASE):
            return True
    
    return False


def detect_placeholders_in_files(file_contents: dict) -> dict:
    """
    Detect placeholders in a dictionary of file contents.
    Returns a dict with file paths as keys and placeholder detection results as values.
    """
    results = {}
    for file_path, content in file_contents.items():
        results[file_path] = contains_placeholder(content)
    return results
