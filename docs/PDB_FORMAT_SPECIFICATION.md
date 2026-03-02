# PDB File Format Specification

Based on analysis of reference `export.pdb` file from rekordbox 6.

## File Structure

- **Page Size**: 4096 bytes
- **Organization**: Page-based structure
- **Page 0**: File header with table pointers
- **Pages 1+**: Data pages (tracks, playlists, etc.)

## File Header (Page 0)

### Offset 0x00-0x0F: Core Header

| Offset | Size | Field | Value |
|--------|------|-------|-------|
| 0x00 | 4 | Magic | `00 00 00 00` |
| 0x04 | 4 | Page Size | `00 10 00 00` (4096) |
| 0x08 | 4 | Unknown | `14 00 00 00` (20) |
| 0x0C | 4 | Unknown | `39 00 00 00` (57) |

### Offset 0x10+: Table Entries

Each table entry is 8 bytes:
- Bytes 0-3: Table ID or value
- Bytes 4-7: Page number or value

Example entries from reference:
- `01 00 00 00 84 00 00 00` → (1, 132)
- `38 00 00 00 01 00 00 00` → (56, 1)

## Track Row Structure

Each track row consists of:
1. **Fixed-width fields section** (approximately 84 bytes)
2. **Variable-width string section** (length depends on content)

### Fixed-Width Fields

| Offset | Size | Field | Example |
|--------|------|-------|---------|
| 0x00 | 4 | Flags/Row Header | `00 00 00 00` |
| 0x04 | 4 | Track ID | `02 00 00 00` (2) |
| 0x08 | 4 | Unknown | `00 00 00 00` (0) |
| 0x0C | 4 | Secondary ID | `33 00 00 00` (51) |
| 0x10 | 4 | File ID | `23 00 00 00` (35) |
| 0x14 | 4 | Unknown | `00 00 00 00` (0) |
| 0x18 | 4 | Date | `09 20 01 24` (2026-01-24) |
| 0x1C | 4 | Unknown | `f6 00 cc 0e` |
| 0x20 | 4 | Duration (ms) | `01 00 08 00` (524289) |
| 0x24 | 4 | Unknown | `00 00 00 00` (0) |
| 0x28 | 4 | Unknown | `24 00 00 00` (36) |
| 0x2C | 4 | Unknown | `00 07 0c 00` (788224) |
| 0x30 | 4 | Sample Rate | `44 ac 00 00` (44100) |
| 0x34+ | ~50 | More fields | Various metadata |

### String Section (Offset ~0x54+)

Strings are stored with length/type prefixes:
- Not traditional null-terminated strings
- Each string appears to have a 1-3 byte prefix
- String types observed:
  - ANLZ file path (starts with `/PIONEER/USBANLZ/`)
  - Artist/title metadata
  - File path (starts with `/Contents/`)

### Example String Data

```
0xb4: 31 03 ... (string length/type prefix)
0xb5: 03 03 ... (data)
...
0xbb: 59 (character 'Y')
0xbc: /PIONEER/USBANLZ/P06B/0001209F/ANLZ0000.DAT
0x17: (separator byte)
...
0x17: 2026-01-24
0x03: (separator byte)
...
```

## String Encoding

- **Path strings**: ASCII/UTF-8
- **Metadata strings**: Mixed encoding
- **Separators**: Bytes like `0x03`, `0x17`, `0xbb` appear between strings

## Key Observations

1. **No traditional page header**: Track pages don't have an 8-byte page header like expected
2. **Variable row size**: Rows are different lengths based on string content
3. **In-page string storage**: Strings are embedded within rows, not in a separate heap
4. **Complex string format**: Strings have unusual encoding with prefix bytes

## Implementation Challenges

1. **String format not fully understood**: The prefix bytes and separators need more analysis
2. **Missing field definitions**: Many fields in the fixed section are unknown
3. **No page headers**: Data pages appear to start directly with row data
4. **Row boundary detection**: Need to understand how rows are separated

## Recommended Implementation Strategy

### Option 1: Copy and Modify (Fastest)
- Copy existing PDB from reference
- Modify only the essential fields (track IDs, paths)
- Keep most structure intact

### Option 2: Pattern-Based Generation
- Generate rows that match the observed pattern
- Use best-guess for unknown fields
- Test with rekordbox and iterate

### Option 3: Deep Reverse Engineering
- Fully decode string format
- Understand all field meanings
- Create complete specification (significant effort)

## Current Status

- ✅ File header structure understood
- ✅ Fixed-width field layout documented
- ⚠️  String format partially understood
- ❌ Many field meanings unknown
- ❌ Row boundary detection unclear

## Next Steps

1. Choose implementation strategy
2. Create PDB writer based on chosen approach
3. Test with rekordbox
4. Iterate based on errors
