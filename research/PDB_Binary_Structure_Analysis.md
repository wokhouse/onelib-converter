# Binary Data Structure Analysis
## PDB (Portable Database) File Format for Rekordbox DJ Software

---

## Executive Summary

This document provides a comprehensive analysis of binary row structures for the PDB file format used by rekordbox DJ software. The analysis focuses on 5 pages containing default metadata that account for the remaining 0.46% (770 bytes) difference from a reference file. The current implementation achieves 99.54% bitwise match (167,166 / 167,936 bytes), with 36 out of 41 pages matching perfectly.

### Current Status
| Metric | Value |
|--------|-------|
| Total bytes matched | 167,166 / 167,936 |
| Match percentage | 99.54% |
| Pages matched perfectly | 36 / 41 |
| Pages requiring analysis | 5 |

---

## 1. COLORS TABLE (Page 14)

### 1.1 String Encoding Discovery

The first byte follows a specific formula for string length encoding:

```
length_marker = strlen(name) * 2 + 3
```

**Verification Table:**

| Name | strlen | Formula (len×2+3) | Hex | Actual Hex | Match |
|------|--------|-------------------|-----|------------|-------|
| Pink | 4 | 11 | 0x0b | 0x0b | ✓ |
| Red | 3 | 9 | 0x09 | 0x09 | ✓ |
| Orange | 6 | 15 | 0x0f | 0x0f | ✓ |
| Yellow | 6 | 15 | 0x0f | 0x0f | ✓ |
| Green | 5 | 13 | 0x0d | 0x0d | ✓ |
| Aqua | 4 | 11 | 0x0b | 0x0b | ✓ |
| Blue | 4 | 11 | 0x0b | 0x0b | ✓ |
| Purple | 6 | 15 | 0x0f | 0x0f | ✓ |

### 1.2 Exact Row Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│ OFFSET   │ SIZE  │ TYPE   │ DESCRIPTION                               │
├─────────────────────────────────────────────────────────────────────────┤
│ 0        │ 1     │ uint8  │ length_marker = strlen(name) * 2 + 3      │
│ 1        │ N     │ ascii  │ name string (NOT null-terminated)         │
│ N+1      │ P     │ bytes  │ padding (nulls) = length_marker - N - 1   │
│                          (total name field = length_marker bytes)      │
│ L-4      │ 1     │ uint8  │ color_id                                  │
│ L-3      │ 1     │ uint8  │ color_id_duplicate (same value)           │
│ L-2      │ 2     │ uint16 │ zero padding (always 0x0000)              │
└─────────────────────────────────────────────────────────────────────────┘

Total row size = 1 + length_marker + 4 bytes
```

### 1.3 Hex Dump Analysis

```
Row 0: 0b 50 69 6e 6b 00 00 00 00 00 00 00 02 02 00 00
       │  │─────────│ │─────────────│ │─────────────│
       │  name="Pink"  padding (7)    id=2, dup, zero
       └─ marker=0x0b (11)

Row 1: 09 52 65 64 00 00 00 00 03 03 00 00
       │  │─────│ │─────│ │─────────│
       │  "Red"  pad(5)  id=3
       └─ 0x09 (9)
```

### 1.4 Extracted Data (All 8 Rows)

| Row # | color_id | name | length_marker | row_size |
|-------|----------|------|---------------|----------|
| 0 | 2 | Pink | 0x0b (11) | 16 bytes |
| 1 | 3 | Red | 0x09 (9) | 14 bytes |
| 2 | 4 | Orange | 0x0f (15) | 20 bytes |
| 3 | 5 | Yellow | 0x0f (15) | 20 bytes |
| 4 | 6 | Green | 0x0d (13) | 18 bytes |
| 5 | 7 | Aqua | 0x0b (11) | 16 bytes |
| 6 | 8 | Blue | 0x0b (11) | 16 bytes |
| 7 | 0 | Purple | 0x0f (15) | 20 bytes |

### 1.5 Key Finding: Current Implementation Error

**Current (INCORRECT) Code:**
```python
def marshal_binary(self, row_index: int) -> bytes:
    name_encoded = encode_device_sql_string(self.name)
    row = bytearray()
    row.extend(struct.pack('<H', 0x12))  # ❌ NOT IN ACTUAL DATA
    row.extend(struct.pack('<H', row_index & 0xFFFF))
    row.extend(struct.pack('<I', self.color_id))
    row.extend(struct.pack('<I', self.color_rgb))
    row.extend(struct.pack('<I', 0))  # unknown
    row.extend(name_encoded)
    return bytes(row)
```

**Correct Implementation:**
```python
def marshal_binary(self, row_index: int) -> bytes:
    row = bytearray()
    
    # String field: [length_marker][name][padding]
    name_bytes = self.name.encode('ascii')
    length_marker = len(name_bytes) * 2 + 3
    padding_len = length_marker - len(name_bytes) - 1
    row.extend(bytes([length_marker]))
    row.extend(name_bytes)
    row.extend(b'\x00' * padding_len)
    
    # ID field: [id][id_dup][00 00]
    row.extend(struct.pack('<B', self.color_id))
    row.extend(struct.pack('<B', self.color_id))
    row.extend(struct.pack('<H', 0))
    
    return bytes(row)
```

---

## 2. COLUMNS TABLE (Page 34)

### 2.1 Marker Pattern Discovery

| Marker | Value | Description |
|--------|-------|-------------|
| Start marker | `0xFFFA` (`fa ff` LE) | Begin of column name |
| End marker | `0xFFFB` (`fb ff` LE) | End of column name |

The column name is encoded as UTF-16LE between these markers.

### 2.2 Exact Row Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│ OFFSET   │ SIZE     │ TYPE    │ DESCRIPTION                            │
├─────────────────────────────────────────────────────────────────────────┤
│ 0        │ 2        │ uint16  │ start_marker = 0xFFFA                  │
│ 2        │ N*2      │ utf16le │ column_name (UTF-16LE encoded)        │
│ N*2+2    │ 2        │ uint16  │ end_marker = 0xFFFB                    │
│ N*2+4    │ 2        │ uint16  │ column_id (sequential: 2,3,4...)       │
│ N*2+6    │ 2        │ uint16  │ field_type (increments: 0x81,0x82...)  │
│ N*2+8    │ 2        │ uint16  │ size_type (e.g., 0x1490, 0x1290)      │
│ N*2+10   │ 2        │ uint16  │ padding (always 0x0000)               │
└─────────────────────────────────────────────────────────────────────────┘

Row size = 12 + (name_length * 2) bytes
```

### 2.3 Hex Dump Analysis

```
Row 0: fa ff 47 00 45 00 4e 00 52 00 45 00 fb ff 00 00 02 00 81 00 90 14 00 00
       │────│ │──────────────────────────│ │────│ │────│ │────│ │────│ │────│
       start  'G'  'E'  'N'  'R'  'E'     end   pad   id=2  type  size  pad
       0xFFFA      (UTF-16LE)             0xFFFB       0x00  0x81 0x1490

Row 1: fa ff 41 00 52 00 54 00 49 00 53 00 54 00 fb ff 03 00 82 00 90 12 00 00
       │────│ │──────────────────────────────────│ │────│ │────│ │────│ │────│
       start  'A'  'R'  'T'  'I'  'S'  'T'        end   id=3  type  size
```

### 2.4 Field Interpretation

| Field | Description | Pattern |
|-------|-------------|---------|
| column_id | Sequential identifier | 2, 3, 4, 5, 6, 7, 8, 9... |
| field_type | Field type code | 0x81, 0x82, 0x83, 0x85, 0x86... (increments, skips 0x84) |
| size_type | Data size/type indicator | 0x1490 (20), 0x1290 (18), 0x1090 (16), 0x0e90 (14), 0x1690 (22) |

### 2.5 Extracted Data (First 9 Columns)

| # | Name | column_id | field_type | size_type | Row Size |
|---|------|-----------|------------|-----------|----------|
| 1 | GENRE | 2 | 0x81 | 0x1490 | 22 bytes |
| 2 | ARTIST | 3 | 0x82 | 0x1290 | 24 bytes |
| 3 | ALBUM | 4 | 0x83 | 0x1290 | 22 bytes |
| 4 | TRACK | 5 | 0x85 | 0x0e90 | 22 bytes |
| 5 | BPM | 6 | 0x86 | 0x1490 | 16 bytes |
| 6 | RATING | 7 | 0x87 | 0x1090 | 22 bytes |
| 7 | YEAR | 8 | 0x88 | 0x1690 | 18 bytes |
| 8 | REMIXER | 9 | 0x89 | 0x1290 | 26 bytes |
| 9 | LABEL | 10 | 0x8A | 0x1290 | 22 bytes |

---

## 3. UNKNOWN17 TABLE (Page 36)

### 3.1 Exact Row Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│ OFFSET   │ SIZE  │ TYPE   │ DESCRIPTION                               │
├─────────────────────────────────────────────────────────────────────────┤
│ 0        │ 2     │ uint16 │ field1 (source_id / from_id)              │
│ 2        │ 2     │ uint16 │ field2 (target_id / to_id)                │
│ 4        │ 4     │ uint32 │ field3 (mapping value / flags)            │
└─────────────────────────────────────────────────────────────────────────┘

Fixed row size = 8 bytes
```

### 3.2 Hex Dump Analysis

```
Row 0:  05 00 06 00 05 01 00 00
        │────│ │────│ │────────│
        f1=5  f2=6  f3=0x00000105 (261)

Row 1:  06 00 07 00 63 01 00 00
        │────│ │────│ │────────│
        f1=6  f2=7  f3=0x00000163 (355)
```

### 3.3 Extracted Data (All 22 Rows)

| Row | field1 | field2 | field3 (hex) | field3 (dec) |
|-----|--------|--------|--------------|--------------|
| 0 | 5 | 6 | 0x00000105 | 261 |
| 1 | 6 | 7 | 0x00000163 | 355 |
| 2 | 7 | 8 | 0x00000163 | 355 |
| 3 | 8 | 9 | 0x00000163 | 355 |
| 4 | 9 | 10 | 0x00000163 | 355 |
| 5 | 10 | 11 | 0x00000163 | 355 |
| 6 | 13 | 15 | 0x00000163 | 355 |
| 7 | 14 | 19 | 0x00000104 | 260 |
| 8 | 15 | 20 | 0x00000106 | 262 |
| 9 | 16 | 21 | 0x00000163 | 355 |
| 10 | 18 | 23 | 0x00000163 | 355 |
| 11 | 2 | 2 | 0x00010002 | 65538 |
| 12 | 3 | 3 | 0x00020003 | 131075 |
| 13 | 4 | 4 | 0x00010003 | 65539 |
| 14 | 11 | 12 | 0x00000063 | 99 |
| 15 | 17 | 5 | 0x00000063 | 99 |
| 16 | 19 | 22 | 0x00000063 | 99 |
| 17 | 20 | 18 | 0x00000063 | 99 |
| 18 | 24 | 17 | 0x00000063 | 99 |
| 19 | 22 | 27 | 0x00000063 | 99 |
| 20 | 26 | 27 | 0x00000063 | 99 |
| 21 | 0 | 0 | 0x00000000 | 0 (empty) |

### 3.4 Pattern Analysis

The `field3` values appear to encode mapping types:

| field3 Value | Occurrences | Possible Meaning |
|--------------|-------------|------------------|
| 0x00000163 (355) | 8 | Standard genre/artist mapping |
| 0x00000105 (261) | 1 | Pink color special mapping |
| 0x00000104 (260) | 1 | Orange color special mapping |
| 0x00000106 (262) | 1 | Yellow color special mapping |
| 0x00000063 (99) | 6 | Lower-level mapping |
| 0x00010002+ | 3 | Self-referential mapping (field1=field2) |

---

## 4. UNKNOWN18 TABLE (Page 38)

### 4.1 Exact Row Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│ OFFSET   │ SIZE  │ TYPE   │ DESCRIPTION                               │
├─────────────────────────────────────────────────────────────────────────┤
│ 0        │ 2     │ uint16 │ field1 (source_id / from_id)              │
│ 2        │ 2     │ uint16 │ field2 (target_id / to_id)                │
│ 4        │ 4     │ uint32 │ field3 (mapping value / flags)            │
└─────────────────────────────────────────────────────────────────────────┘

Fixed row size = 8 bytes (IDENTICAL to UNKNOWN17 structure)
```

### 4.2 Hex Dump Analysis

```
Row 0:  15 00 07 00 01 00 00 00
        │────│ │────│ │────────│
        f1=21 f2=7  f3=0x00000001 (1)

Row 1:  0e 00 08 00 01 00 00 00
        │────│ │────│ │────────│
        f1=14 f2=8  f3=0x00000001 (1)
```

### 4.3 Extracted Data (All 18 Rows)

| Row | field1 | field2 | field3 (hex) | field3 (dec) |
|-----|--------|--------|--------------|--------------|
| 0 | 21 | 7 | 0x00000001 | 1 |
| 1 | 14 | 8 | 0x00000001 | 1 |
| 2 | 8 | 9 | 0x00000001 | 1 |
| 3 | 9 | 10 | 0x00000001 | 1 |
| 4 | 10 | 11 | 0x00000001 | 1 |
| 5 | 15 | 13 | 0x00000001 | 1 |
| 6 | 13 | 15 | 0x00000001 | 1 |
| 7 | 23 | 16 | 0x00000001 | 1 |
| 8 | 22 | 17 | 0x00000001 | 1 |
| 9 | 25 | 0 | 0x00000100 | 256 |
| 10 | 26 | 1 | 0x00000200 | 512 |
| 11 | 2 | 2 | 0x00030000 | 196608 |
| 12 | 3 | 3 | 0x00040000 | 262144 |
| 13 | 4 | 4 | 0x00050000 | 327680 |
| 14 | 5 | 5 | 0x00060000 | 393216 |
| 15 | 11 | 12 | 0x00070000 | 458752 |
| 16 | 0 | 0 | 0x00000000 | 0 (empty) |
| 17 | 0 | 0 | 0x00000000 | 0 (empty) |

### 4.4 Pattern Analysis

| field3 Pattern | Rows | Interpretation |
|----------------|------|----------------|
| 0x00000001 | 0-8 | Simple boolean/active flag |
| 0x00000100-0x00000200 | 9-10 | Special flags (256, 512) |
| 0x000N0000 | 11-15 | Encoded as `(row_index + 3) << 16` |

---

## 5. HISTORY TABLE (Page 40)

### 5.1 String Encoding Pattern

Same encoding as COLORS table:
```
length_marker = strlen(string) * 2 + 3
```

### 5.2 Exact Row Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│ OFFSET   │ SIZE     │ TYPE   │ DESCRIPTION                             │
├─────────────────────────────────────────────────────────────────────────┤
│ 0        │ 4        │ bytes  │ header (always 0x00000000)              │
│ 4        │ 1        │ uint8  │ date_length_marker                      │
│ 5        │ N        │ ascii  │ date string (e.g., "2026-03-02")        │
│ 5+N      │ P        │ bytes  │ padding (nulls to fill length_marker)   │
│ L        │ 1        │ uint8  │ unknown1 (observed: 0x19 = 25)          │
│ L+1      │ 1        │ uint8  │ unknown2 (observed: 0x1e = 30)          │
│ L+2      │ 1        │ uint8  │ name_length_marker                      │
│ L+3      │ M        │ ascii  │ name string (e.g., "1000")              │
│ L+3+M    │ Q        │ bytes  │ padding (nulls to fill length_marker)   │
│ L+3+M+Q  │ 1        │ uint8  │ unknown3 (observed: 0x03 = 3)           │
│ rest     │ varies   │ bytes  │ padding (nulls to fill page)            │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Hex Dump Analysis

```
00: 00 00 00 00 17 32 30 32 36 2d 30 33 2d 30 32 19
    │────────│ │  │─────────────────────────│ │
    header    len "2  0  2  6  -  0  3  -  0  2" unk1
    (zeros)   23   (date = "2026-03-02")        25

10: 1e 0b 31 30 30 30 03 00 00 00 00 00 00 00 00 00
    │  │  │────────│ │
   unk2 len "1  0  0  0"  unk3
    30  11 (name)       3

20: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    └─────────────────────────────────────────────│
                    padding (rest of page)
```

### 5.4 Decoded Row Data

| Field | Value | Notes |
|-------|-------|-------|
| header | 0x00000000 | 4 zero bytes |
| date | "2026-03-02" | 10 chars, marker=0x17 (23) |
| unknown1 | 0x19 (25) | Possibly row type or table ID |
| unknown2 | 0x1e (30) | Possibly total row size or timestamp |
| name | "1000" | 4 chars, marker=0x0b (11) |
| unknown3 | 0x03 (3) | Possibly entry count or version |

### 5.5 Unknown Bytes Interpretation

| Byte | Value | Possible Meanings |
|------|-------|-------------------|
| 0x19 | 25 | Row type ID, table reference, or field count |
| 0x1e | 30 | Row size indicator, timestamp component |
| 0x03 | 3 | Entry count, status flag, version number |

---

## 6. Python Implementation

### 6.1 String Encoding Functions

```python
def encode_pdb_string(s: str) -> bytes:
    """
    Encode string for PDB format.
    Format: [length_marker][ascii_string][padding]
    length_marker = strlen(s) * 2 + 3
    """
    name_bytes = s.encode('ascii')
    length_marker = len(name_bytes) * 2 + 3
    padding_len = length_marker - len(name_bytes) - 1
    return bytes([length_marker]) + name_bytes + b'\x00' * padding_len


def decode_pdb_string(data: bytes, offset: int) -> tuple[str, int]:
    """
    Decode PDB-encoded string from data at offset.
    Returns (decoded_string, bytes_consumed).
    """
    length_marker = data[offset]
    string_len = (length_marker - 3) // 2
    name = data[offset + 1: offset + 1 + string_len].decode('ascii')
    bytes_consumed = 1 + length_marker
    return name, bytes_consumed
```

### 6.2 ColorRow Dataclass

```python
import struct
from dataclasses import dataclass

@dataclass
class ColorRow:
    """Row structure for COLORS table (Page 14)."""
    color_id: int
    name: str
    rgb_value: int = 0
    
    def marshal_binary(self, row_index: int) -> bytes:
        """Serialize to binary format."""
        row = bytearray()
        
        # String field: [length_marker][name][padding]
        name_bytes = self.name.encode('ascii')
        length_marker = len(name_bytes) * 2 + 3
        padding_len = length_marker - len(name_bytes) - 1
        row.extend(bytes([length_marker]))
        row.extend(name_bytes)
        row.extend(b'\x00' * padding_len)
        
        # ID field: [id][id_dup][00 00]
        row.extend(struct.pack('<B', self.color_id))
        row.extend(struct.pack('<B', self.color_id))
        row.extend(struct.pack('<H', 0))
        
        return bytes(row)
    
    @classmethod
    def unmarshal_binary(cls, data: bytes, offset: int = 0) -> tuple['ColorRow', int]:
        """Deserialize from binary data."""
        name, consumed = decode_pdb_string(data, offset)
        offset += consumed
        color_id = data[offset]
        return cls(color_id=color_id, name=name), offset + 4
```

### 6.3 ColumnRow Dataclass

```python
@dataclass
class ColumnRow:
    """Row structure for COLUMNS table (Page 34)."""
    column_id: int
    name: str
    field_type: int
    size_type: int
    
    def marshal_binary(self, row_index: int) -> bytes:
        """Serialize to binary format."""
        row = bytearray()
        
        # Start marker
        row.extend(struct.pack('<H', 0xFFFA))
        
        # Name in UTF-16LE
        name_utf16 = self.name.encode('utf-16-le')
        row.extend(name_utf16)
        
        # End marker
        row.extend(struct.pack('<H', 0xFFFB))
        
        # Metadata
        row.extend(struct.pack('<H', self.column_id))
        row.extend(struct.pack('<H', self.field_type))
        row.extend(struct.pack('<H', self.size_type))
        row.extend(struct.pack('<H', 0))
        
        return bytes(row)
```

### 6.4 Unknown17Row / Unknown18Row Dataclass

```python
@dataclass
class Unknown17Row:
    """Row structure for UNKNOWN17 table (Page 36)."""
    field1: int
    field2: int
    field3: int
    
    def marshal_binary(self, row_index: int) -> bytes:
        """Serialize to binary format."""
        row = bytearray()
        row.extend(struct.pack('<H', self.field1))
        row.extend(struct.pack('<H', self.field2))
        row.extend(struct.pack('<I', self.field3))
        return bytes(row)


@dataclass
class Unknown18Row:
    """Row structure for UNKNOWN18 table (Page 38)."""
    field1: int
    field2: int
    field3: int
    
    def marshal_binary(self, row_index: int) -> bytes:
        """Serialize to binary format (same as Unknown17Row)."""
        row = bytearray()
        row.extend(struct.pack('<H', self.field1))
        row.extend(struct.pack('<H', self.field2))
        row.extend(struct.pack('<I', self.field3))
        return bytes(row)
```

### 6.5 HistoryRow Dataclass

```python
@dataclass
class HistoryRow:
    """Row structure for HISTORY table (Page 40)."""
    date: str
    name: str
    unknown1: int = 0x19
    unknown2: int = 0x1e
    unknown3: int = 0x03
    
    def marshal_binary(self, row_index: int) -> bytes:
        """Serialize to binary format."""
        row = bytearray()
        
        # Header (4 zero bytes)
        row.extend(b'\x00' * 4)
        
        # Date field
        row.extend(encode_pdb_string(self.date))
        
        # Unknown bytes
        row.extend(struct.pack('<B', self.unknown1))
        row.extend(struct.pack('<B', self.unknown2))
        
        # Name field
        row.extend(encode_pdb_string(self.name))
        
        # Final unknown byte
        row.extend(struct.pack('<B', self.unknown3))
        
        return bytes(row)
```

---

## 7. Default Data Initialization

### 7.1 Get Default Colors

```python
def get_default_colors() -> list[ColorRow]:
    """Get default color entries for rekordbox PDB."""
    return [
        ColorRow(color_id=2, name="Pink"),
        ColorRow(color_id=3, name="Red"),
        ColorRow(color_id=4, name="Orange"),
        ColorRow(color_id=5, name="Yellow"),
        ColorRow(color_id=6, name="Green"),
        ColorRow(color_id=7, name="Aqua"),
        ColorRow(color_id=8, name="Blue"),
        ColorRow(color_id=0, name="Purple"),
    ]
```

### 7.2 Get Default Columns

```python
def get_default_columns() -> list[ColumnRow]:
    """Get default column entries for rekordbox PDB."""
    return [
        ColumnRow(2, "GENRE", 0x81, 0x1490),
        ColumnRow(3, "ARTIST", 0x82, 0x1290),
        ColumnRow(4, "ALBUM", 0x83, 0x1290),
        ColumnRow(5, "TRACK", 0x85, 0x0e90),
        ColumnRow(6, "BPM", 0x86, 0x1490),
        ColumnRow(7, "RATING", 0x87, 0x1090),
        ColumnRow(8, "YEAR", 0x88, 0x1690),
        ColumnRow(9, "REMIXER", 0x89, 0x1290),
        ColumnRow(10, "LABEL", 0x8A, 0x1290),
        # ... continue for remaining columns
    ]
```

### 7.3 Get Default Unknown17

```python
def get_default_unknown17() -> list[Unknown17Row]:
    """Get default UNKNOWN17 mapping entries."""
    return [
        Unknown17Row(5, 6, 0x00000105),
        Unknown17Row(6, 7, 0x00000163),
        Unknown17Row(7, 8, 0x00000163),
        Unknown17Row(8, 9, 0x00000163),
        Unknown17Row(9, 10, 0x00000163),
        Unknown17Row(10, 11, 0x00000163),
        Unknown17Row(13, 15, 0x00000163),
        Unknown17Row(14, 19, 0x00000104),
        Unknown17Row(15, 20, 0x00000106),
        Unknown17Row(16, 21, 0x00000163),
        Unknown17Row(18, 23, 0x00000163),
        Unknown17Row(2, 2, 0x00010002),
        Unknown17Row(3, 3, 0x00020003),
        Unknown17Row(4, 4, 0x00010003),
        Unknown17Row(11, 12, 0x00000063),
        Unknown17Row(17, 5, 0x00000063),
        Unknown17Row(19, 22, 0x00000063),
        Unknown17Row(20, 18, 0x00000063),
        Unknown17Row(24, 17, 0x00000063),
        Unknown17Row(22, 27, 0x00000063),
        Unknown17Row(26, 27, 0x00000063),
    ]
```

### 7.4 Get Default Unknown18

```python
def get_default_unknown18() -> list[Unknown18Row]:
    """Get default UNKNOWN18 mapping entries."""
    return [
        Unknown18Row(21, 7, 0x00000001),
        Unknown18Row(14, 8, 0x00000001),
        Unknown18Row(8, 9, 0x00000001),
        Unknown18Row(9, 10, 0x00000001),
        Unknown18Row(10, 11, 0x00000001),
        Unknown18Row(15, 13, 0x00000001),
        Unknown18Row(13, 15, 0x00000001),
        Unknown18Row(23, 16, 0x00000001),
        Unknown18Row(22, 17, 0x00000001),
        Unknown18Row(25, 0, 0x00000100),
        Unknown18Row(26, 1, 0x00000200),
        Unknown18Row(2, 2, 0x00030000),
        Unknown18Row(3, 3, 0x00040000),
        Unknown18Row(4, 4, 0x00050000),
        Unknown18Row(5, 5, 0x00060000),
        Unknown18Row(11, 12, 0x00070000),
    ]
```

---

## 8. Summary

### 8.1 Key Discoveries

1. **String Encoding Formula**: `length_marker = strlen(name) * 2 + 3` for ASCII strings
2. **UTF-16LE Markers**: `0xFFFA` (start) and `0xFFFB` (end) for column names
3. **Fixed-Size Rows**: UNKNOWN17 and UNKNOWN18 both use 8-byte fixed rows
4. **Variable-Size Rows**: COLORS, COLUMNS, HISTORY use length-prefixed strings

### 8.2 Implementation Corrections Needed

| Table | Current Issue | Correct Approach |
|-------|---------------|------------------|
| COLORS | Uses DeviceSQL encoding with row_offset | Use simple length_marker encoding |
| COLUMNS | Check marker handling | Use 0xFFFA/0xFFFB markers with UTF-16LE |
| UNKNOWN17/18 | Should be straightforward | Simple 3-field structure |
| HISTORY | Verify string encoding | Same as COLORS for date/name fields |

### 8.3 Remaining Work

- [ ] Verify all 27 column entries
- [ ] Test binary output matches reference byte-for-byte
- [ ] Document the semantic meaning of field3 values in UNKNOWN17/18

---

*Document generated for PDB binary structure analysis*
*Target: 100% bitwise match with reference file*
