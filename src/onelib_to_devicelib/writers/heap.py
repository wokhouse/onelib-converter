"""
Two-Way Heap Allocator

Manages page heap with top growing forward (rows) and bottom growing backward (row index).
"""


class TwoWayHeap:
    """Two-way heap allocator for PDB pages.

    The heap grows from both ends:
    - Top: Row data grows forward
    - Bottom: Row index (RowSets) grows backward
    - Middle: Padding fills the gap
    """

    def __init__(self, page_size: int = 4096, data_header_size: int = 40):
        """Initialize two-way heap.

        Args:
            page_size: Total page size in bytes (default 4096)
            data_header_size: Size of page header to reserve (40 for 32-byte page + 8-byte data header)

        Note: The heap_prefix is stored separately for special pages (Columns, Unknown18)
        but is NOT included in to_bytes() output for normal pages.
        """
        self.page_size = page_size
        self.data_header_size = data_header_size
        # Heap size is page_size minus data_header_size (48 bytes)
        # We no longer subtract 8 bytes for heap_prefix since it's not in to_bytes() output
        self.heap_size = page_size - data_header_size
        self.top_cursor = 0
        self.bottom_cursor = self.heap_size
        self.top_data = bytearray()
        self.bottom_data = bytearray()
        self.heap_prefix = b'\x00' * 8  # Metadata for special pages (Columns, Unknown18)

    def write_top(self, data: bytes) -> int:
        """Write data to top of heap (row data).

        Args:
            data: Bytes to write

        Returns:
            Offset from start of heap where data was written
        """
        offset = self.top_cursor
        self.top_data += data
        self.top_cursor += len(data)
        return offset

    def write_bottom(self, data: bytes) -> int:
        """Write data to bottom of heap (row index).

        Args:
            data: Bytes to write

        Returns:
            Offset from end of heap where data was written (0 = first from bottom)
        """
        self.bottom_data = data + self.bottom_data
        self.bottom_cursor -= len(data)
        # Return offset from end (0 = first item from end)
        return self.heap_size - self.bottom_cursor - len(data)

    def align_top(self, alignment: int = 4):
        """Align top cursor to specified boundary.

        Args:
            alignment: Boundary to align to (default 4 bytes)
        """
        padding = (alignment - (self.top_cursor % alignment)) % alignment
        if padding:
            self.top_data += b'\x00' * padding
            self.top_cursor += padding

    def align_bottom(self, alignment: int = 4):
        """Align bottom cursor to specified boundary.

        Args:
            alignment: Boundary to align to (default 4 bytes)
        """
        padding = (self.bottom_cursor % alignment) % alignment
        if padding:
            self.bottom_data = b'\x00' * padding + self.bottom_data
            self.bottom_cursor -= padding

    def free_size(self) -> int:
        """Calculate remaining free space in heap.

        Returns:
            Number of bytes free between top and bottom cursors
        """
        return max(0, self.bottom_cursor - self.top_cursor)

    def set_prefix(self, prefix: bytes) -> None:
        """Set the 8-byte heap prefix.

        The heap prefix is stored at bytes 40-48 of the page (before the data header).
        For some tables (Columns, Unknown18), this contains metadata for the first row.

        Args:
            prefix: Exactly 8 bytes for the heap prefix
        """
        if len(prefix) != 8:
            raise ValueError(f"Heap prefix must be exactly 8 bytes, got {len(prefix)}")
        self.heap_prefix = prefix

    def to_bytes(self) -> bytes:
        """Combine top and bottom into final heap data.

        Returns:
            Heap data WITHOUT prefix: top_data + padding + bottom_data

        Note: The heap_prefix is NOT included in output. For normal pages,
        the data header (bytes 48-63) is written separately by DataPage.
        For special pages (Columns, Unknown18), the heap_prefix is handled
        differently via raw_page_bytes override.
        """
        # Don't include heap_prefix - page structure handles it separately
        padding = self.bottom_cursor - self.top_cursor
        return bytes(self.top_data + (b'\x00' * padding) + self.bottom_data)

    def __repr__(self) -> str:
        """String representation of heap state."""
        return (f"TwoWayHeap(page_size={self.page_size}, "
                f"top_cursor={self.top_cursor}, bottom_cursor={self.bottom_cursor}, "
                f"free={self.free_size()})")
