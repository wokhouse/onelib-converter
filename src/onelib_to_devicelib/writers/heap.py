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

    def __init__(self, page_size: int = 4096, data_header_size: int = 48):
        """Initialize two-way heap.

        Args:
            page_size: Total page size in bytes (default 4096)
            data_header_size: Size of page header to reserve (40 for page header + 8 for data header)
        """
        self.page_size = page_size
        self.data_header_size = data_header_size
        self.heap_size = page_size - data_header_size
        self.top_cursor = 0
        self.bottom_cursor = self.heap_size
        self.top_data = bytearray()
        self.bottom_data = bytearray()

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

    def to_bytes(self) -> bytes:
        """Combine top and bottom into final page heap.

        Returns:
            Complete heap bytes with padding in the middle
        """
        padding = self.bottom_cursor - self.top_cursor
        return bytes(self.top_data + (b'\x00' * padding) + self.bottom_data)

    def __repr__(self) -> str:
        """String representation of heap state."""
        return (f"TwoWayHeap(page_size={self.page_size}, "
                f"top_cursor={self.top_cursor}, bottom_cursor={self.bottom_cursor}, "
                f"free={self.free_size()})")
