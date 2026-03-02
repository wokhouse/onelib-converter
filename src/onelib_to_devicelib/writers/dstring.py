"""
DeviceSQL String Encoder

Encodes strings in the three DeviceSQL formats used in rekordbox PDB files.
"""

import struct


def encode_device_sql_string(s: str) -> bytes:
    """
    Encode string in DeviceSQL format.

    Three formats:
    1. Short ASCII (≤127 bytes): ((len+1) << 1) | 0x01 + content
    2. Long ASCII (>127 bytes): 0x40 + 0x03 + u16_length + content
    3. UTF-16LE: 0x90 + 0x03 + u16_length + utf16_content

    Args:
        s: String to encode

    Returns:
        Encoded bytes in DeviceSQL format
    """
    # Empty string case
    if not s:
        return bytes([0x01])

    utf16 = s.encode('utf-16-le')

    # Check if ASCII-only
    try:
        ascii_bytes = s.encode('ascii')
        if len(ascii_bytes) <= 127:
            # Short ASCII format
            # Length byte: ((length + 1) << 1) | 0x01
            # The +1 accounts for the length byte itself
            length_byte = ((len(ascii_bytes) + 1) << 1) | 0x01
            return bytes([length_byte]) + ascii_bytes
        else:
            # Long ASCII format
            # Header: 0x40 0x03
            # Length: u16
            return bytes([0x40, 0x03]) + struct.pack('<H', len(ascii_bytes)) + ascii_bytes
    except UnicodeEncodeError:
        # UTF-16LE format
        # Header: 0x90 0x03
        # Length: u16 (number of bytes, not characters)
        return bytes([0x90, 0x03]) + struct.pack('<H', len(utf16)) + utf16


def decode_device_sql_string(data: bytes, offset: int = 0) -> tuple[str, int]:
    """
    Decode a DeviceSQL string.

    Args:
        data: Bytes containing the encoded string
        offset: Offset to start reading from

    Returns:
        Tuple of (decoded_string, next_offset)

    Raises:
        ValueError: If the string format is invalid
    """
    if offset >= len(data):
        return "", offset

    first_byte = data[offset]

    # Check format type from first byte
    if first_byte & 0x01:  # Short ASCII format
        # Length is (first_byte >> 1) - 1
        # The -1 accounts for the length byte itself
        length = (first_byte >> 1) - 1
        if offset + 1 + length > len(data):
            raise ValueError(f"Short ASCII string extends beyond data: length={length}, available={len(data) - offset - 1}")
        string_data = data[offset + 1:offset + 1 + length]
        return string_data.decode('ascii'), offset + 1 + length

    elif first_byte == 0x40:  # Long ASCII format
        if offset + 3 > len(data):
            raise ValueError("Long ASCII header extends beyond data")
        length = struct.unpack('<H', data[offset + 2:offset + 4])[0]
        if offset + 4 + length > len(data):
            raise ValueError(f"Long ASCII string extends beyond data: length={length}, available={len(data) - offset - 4}")
        string_data = data[offset + 4:offset + 4 + length]
        return string_data.decode('ascii'), offset + 4 + length

    elif first_byte == 0x90:  # UTF-16LE format
        if offset + 3 > len(data):
            raise ValueError("UTF-16LE header extends beyond data")
        length = struct.unpack('<H', data[offset + 2:offset + 4])[0]
        if offset + 4 + length > len(data):
            raise ValueError(f"UTF-16LE string extends beyond data: length={length}, available={len(data) - offset - 4}")
        string_data = data[offset + 4:offset + 4 + length]
        return string_data.decode('utf-16-le'), offset + 4 + length

    elif first_byte == 0x01:  # Empty string
        return "", offset + 1

    else:
        raise ValueError(f"Unknown DeviceSQL string format: first_byte=0x{first_byte:02x}")


def get_encoded_length(s: str) -> int:
    """
    Calculate the length of a string when encoded in DeviceSQL format.

    Args:
        s: String to measure

    Returns:
        Length in bytes when encoded
    """
    return len(encode_device_sql_string(s))
