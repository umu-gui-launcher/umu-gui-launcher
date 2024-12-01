import struct
import magic

def is_windows_executable(file_path):
    """Check if a file is a Windows executable using multiple methods"""
    try:
        # First try using python-magic
        file_type = magic.from_file(file_path)
        if "PE32" in file_type or "MS-DOS" in file_type:
            return True
        
        # Fallback: Check PE header signature
        with open(file_path, 'rb') as f:
            # Read DOS header
            if f.read(2) != b'MZ':
                return False
                
            # Get offset to PE header
            f.seek(0x3c)
            pe_offset = struct.unpack('I', f.read(4))[0]
            
            # Check PE signature
            f.seek(pe_offset)
            return f.read(4) == b'PE\0\0'
            
    except Exception:
        return False
