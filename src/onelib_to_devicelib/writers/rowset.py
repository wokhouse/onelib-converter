"""
Row Index Structure (RowSet)

Manages row presence flags and positions in PDB pages.
"""

import struct
from dataclasses import dataclass, field
from typing import List


@dataclass
class RowSet:
    """Row index structure for 16 rows.

    A RowSet tracks which rows exist in a page and their positions.
    Each RowSet can track up to 16 rows.

    Attributes:
        positions: List of 16 uint16 values (32 bytes total) - row offsets
        active_rows: Bitmask of which rows exist (2 bytes)
        last_written_rows: Bitmask of which rows were last modified (2 bytes)
    """
    positions: List[int] = field(default_factory=lambda: [0] * 16)  # 32 bytes
    active_rows: int = 0  # 2 bytes - bitmask of existing rows
    last_written_rows: int = 0  # 2 bytes - bitmask of modified rows

    def set_row(self, index: int, position: int):
        """Set row position and mark as active.

        Args:
            index: Row index (0-15)
            position: Offset from page data start where row is stored

        Raises:
            IndexError: If index is out of range (not 0-15)
            ValueError: If position is out of valid range
        """
        if not 0 <= index < 16:
            raise IndexError(f"Row index must be 0-15, got {index}")

        if position < 0 or position > 0xFFFF:
            raise ValueError(f"Position must be 0-0xFFFF, got {position}")

        self.positions[index] = position
        self.active_rows |= (1 << index)
        self.last_written_rows = (1 << index)

    def row_exists(self, index: int) -> bool:
        """Check if row exists.

        Args:
            index: Row index (0-15)

        Returns:
            True if row exists, False otherwise
        """
        if not 0 <= index < 16:
            return False
        return (self.active_rows & (1 << index)) != 0

    def clear_row(self, index: int):
        """Clear row (mark as inactive).

        Args:
            index: Row index (0-15)

        Raises:
            IndexError: If index is out of range (not 0-15)
        """
        if not 0 <= index < 16:
            raise IndexError(f"Row index must be 0-15, got {index}")

        self.active_rows &= ~(1 << index)
        self.positions[index] = 0

    def count_rows(self) -> int:
        """Count number of active rows.

        Returns:
            Number of rows that exist in this RowSet
        """
        return bin(self.active_rows).count('1')

    def marshal_binary(self) -> bytes:
        """Serialize to bytes.

        The positions are written reversed (as in REX implementation).
        Format: 16 × uint16 (reversed) + uint16 (active_rows) + uint16 (last_written)

        Returns:
            36 bytes of serialized RowSet data
        """
        # REX reverses positions before writing
        reversed_positions = self.positions[::-1]
        position_bytes = struct.pack('<' + 'H' * 16, *reversed_positions)
        flag_bytes = struct.pack('<HH', self.active_rows, self.last_written_rows)
        return position_bytes + flag_bytes

    @classmethod
    def unmarshal_binary(cls, data: bytes, offset: int = 0) -> 'RowSet':
        """Deserialize from bytes.

        Args:
            data: Bytes containing serialized RowSet
            offset: Offset to start reading from

        Returns:
            RowSet instance

        Raises:
            ValueError: If data is too short
        """
        if offset + 36 > len(data):
            raise ValueError(f"Need 36 bytes for RowSet, got {len(data) - offset}")

        # Read 16 uint16 positions (reversed)
        positions = list(struct.unpack('<' + 'H' * 16, data[offset:offset + 32]))
        # Reverse back to normal order
        positions = positions[::-1]

        # Read flags
        active_rows, last_written = struct.unpack('<HH', data[offset + 32:offset + 36])

        return cls(positions=positions, active_rows=active_rows, last_written_rows=last_written)

    def __repr__(self) -> str:
        """String representation of RowSet state."""
        return (f"RowSet(active={self.count_rows()}/16, "
                f"active_rows=0x{self.active_rows:04x}, "
                f"last_written=0x{self.last_written_rows:04x})")
