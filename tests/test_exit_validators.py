import os
import tempfile
import pytest
from exit_validators import load_private_keys

def test_load_private_keys_mixed_formats():
    """Test loading private keys with mixed 'privateKey:' and '0x' formats."""
    content = """
    # Comments starting with hash
    privateKey: "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    
    # Another format
    0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890
    
    # Indented
      privateKey: '0x1111111111111111111111111111111111111111111111111111111111111111'
      
    # Indented raw
        0x2222222222222222222222222222222222222222222222222222222222222222
        
    garbage line
    another garbage
    """
    
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
        
    try:
        keys = load_private_keys(tmp_path)
        
        expected_keys = [
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "0x1111111111111111111111111111111111111111111111111111111111111111",
            "0x2222222222222222222222222222222222222222222222222222222222222222"
        ]
        
        assert len(keys) == 4
        assert keys == expected_keys
        
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_load_private_keys_empty_file():
    """Test loading from an empty file."""
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
        tmp_path = tmp.name
        
    try:
        keys = load_private_keys(tmp_path)
        assert keys == []
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_load_private_keys_no_valid_keys():
    """Test loading from a file with no valid keys."""
    content = """
    just text
    more text
    key: value
    """
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
        
    try:
        keys = load_private_keys(tmp_path)
        assert keys == []
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
