"""
ANLZ (Analysis) file writer.

Generates ANLZ0000.DAT, ANLZ0000.EXT, and ANLZ0000.2EX files
containing waveform, beat grid, and cue point data.

Based on:
- Deep-Symmetry analysis documentation
- Implementation research results
"""

import logging
import struct
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


class ANLZGenerator:
    """
    Generates Rekordbox ANLZ analysis files.

    Creates all three ANLZ file types with proper PMAI headers and tags.
    """

    MAGIC = b'PMAI'

    # Tag fourcc codes
    TAG_PPTH = b'PPTH'  # Path Information
    TAG_PWV3 = b'PWV3'  # Mono Waveform
    TAG_PWV5 = b'PWV5'  # Color Waveform
    TAG_PPOS = b'PPOS'  # Beat Grid Positions
    TAG_PCOB = b'PCOB'  # Cue Points

    def __init__(self, track_path: str, bpm: float, duration_ms: int):
        """
        Initialize the ANLZ generator.

        Args:
            track_path: File path of the track
            bpm: BPM value
            duration_ms: Duration in milliseconds
        """
        self.track_path = track_path
        self.bpm = bpm
        self.duration_ms = duration_ms
        self.tags = []

    def _write_pmai_header(self, content_size: int, num_tags: int) -> bytes:
        """Write PMAI file header."""
        header = bytearray(20)  # PMAI header size

        # Magic
        header[0:4] = self.MAGIC

        # File size (header + content)
        struct.pack_into('<I', header, 4, 20 + content_size)

        # Unknown fields
        struct.pack_into('<I', header, 8, 1)  # Version?
        struct.pack_into('<I', header, 12, num_tags)
        struct.pack_into('<I', header, 16, 0)

        return bytes(header)

    def _create_ppth_tag(self, path: str) -> bytes:
        """Create PPTH (path) tag."""
        # Encode path as UTF-16LE
        path_data = path.encode('utf-16-le') + b'\x00\x00'

        # Tag: fourcc + length + data
        tag = bytearray()
        tag += self.TAG_PPTH
        tag += struct.pack('<I', len(path_data) + 8)  # Tag size
        tag += struct.pack('<I', 0)  # Unknown
        tag += path_data

        return bytes(tag)

    def _create_pwv3_tag(self, waveform_data: bytes) -> bytes:
        """Create PWV3 (mono waveform preview) tag."""
        tag = bytearray()
        tag += self.TAG_PWV3
        tag += struct.pack('<I', len(waveform_data) + 16)  # Tag size
        tag += struct.pack('<H', 1)  # Unknown
        tag += struct.pack('<H', 0)  # Unknown
        tag += struct.pack('<I', len(waveform_data))  # Data length
        tag += waveform_data

        return bytes(tag)

    def _create_ppos_tag(self, beats: List[Tuple[int, int, int]]) -> bytes:
        """Create PPOS (beat grid) tag.

        Args:
            beats: List of (beat_number, tempo, time_ms) tuples
        """
        # Beat entries
        beat_data = bytearray()
        for beat_num, tempo, time_ms in beats:
            beat_data += struct.pack('<B', beat_num)  # Beat number
            beat_data += struct.pack('<B', (tempo // 100) if tempo > 100 else tempo)  # Tempo
            beat_data += struct.pack('<H', time_ms)  # Time in ms
            beat_data += struct.pack('<I', 0)  # Reserved

        # Tag
        tag = bytearray()
        tag += self.TAG_PPOS
        tag += struct.pack('<I', len(beat_data) + 20)
        tag += struct.pack('<I', len(beats))  # Number of beats
        tag += struct.pack('<I', 0)  # Unknown
        tag += struct.pack('<I', 0)  # Unknown
        tag += beat_data

        return bytes(tag)

    def _create_pcob_tag(self, cues: List[Dict]) -> bytes:
        """Create PCOB (cue points) tag."""
        # Cue entry structure
        cue_data = bytearray()
        for cue in cues:
            cue_data += struct.pack('<I', cue.get('id', 0))
            cue_data += struct.pack('<I', cue.get('position_ms', 0))
            cue_data += struct.pack('<I', 0)  # Unknown
            cue_data += struct.pack('<B', cue.get('type', 0))  # Cue type
            cue_data += b'\x00' * 3  # Padding

        tag = bytearray()
        tag += self.TAG_PCOB
        tag += struct.pack('<I', len(cue_data) + 16)
        tag += struct.pack('<I', len(cues))
        tag += struct.pack('<I', 0)
        tag += struct.pack('<I', 0)
        tag += cue_data

        return bytes(tag)

    def write_dat_file(self, output_path: Path) -> None:
        """Write ANLZ0000.DAT file."""
        tags = []
        tags.append(self._create_ppth_tag(self.track_path))

        # Build file content
        content = bytearray()
        for tag in tags:
            content += tag

        # Header
        header = self._write_pmai_header(len(content), len(tags))

        with open(output_path, 'wb') as f:
            f.write(header)
            f.write(content)

        logger.debug(f"Wrote DAT file: {output_path}")

    def write_ext_file(self, output_path: Path, waveform: bytes) -> None:
        """Write ANLZ0000.EXT file with waveform."""
        tags = []
        tags.append(self._create_pwv3_tag(waveform))

        content = bytearray()
        for tag in tags:
            content += tag

        header = self._write_pmai_header(len(content), len(tags))

        with open(output_path, 'wb') as f:
            f.write(header)
            f.write(content)

        logger.debug(f"Wrote EXT file: {output_path}")

    def write_2ex_file(
        self,
        output_path: Path,
        waveform_color: bytes,
        beats: List[Tuple[int, int, int]],
        cues: List[Dict]
    ) -> None:
        """Write ANLZ0000.2EX file."""
        tags = []

        # PWV5 (color waveform) - optional for MVP
        if waveform_color:
            pwv5 = bytearray()
            pwv5 += self.TAG_PWV5
            pwv5 += struct.pack('<I', len(waveform_color) + 16)
            pwv5 += struct.pack('<I', 0)
            pwv5 += struct.pack('<I', 1200)  # Columns
            pwv5 += waveform_color
            tags.append(bytes(pwv5))

        # PPOS (beat grid)
        tags.append(self._create_ppos_tag(beats))

        # PCOB (cues)
        if cues:
            tags.append(self._create_pcob_tag(cues))

        content = bytearray()
        for tag in tags:
            content += tag

        header = self._write_pmai_header(len(content), len(tags))

        with open(output_path, 'wb') as f:
            f.write(header)
            f.write(content)

        logger.debug(f"Wrote 2EX file: {output_path}")


def generate_mono_waveform(audio_path: str, num_samples: int = 400) -> bytes:
    """Generate mono waveform preview for PWV3 tag.

    Args:
        audio_path: Path to audio file
        num_samples: Number of samples for preview (default 400)

    Returns:
        Waveform data as bytes (0-255 range)
    """
    try:
        import librosa
    except ImportError:
        logger.warning("librosa not installed. Cannot generate waveforms.")
        # Return minimal waveform
        return bytes(num_samples)

    try:
        # Load audio
        y, sr = librosa.load(audio_path, sr=None, mono=True)

        # Calculate hop length for desired number of samples
        hop_length = max(1, len(y) // num_samples)

        # Calculate RMS energy per frame
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]

        # Normalize to 0-255 range
        if rms.max() > 0:
            rms_normalized = (rms / rms.max() * 255).astype(np.uint8)
        else:
            rms_normalized = np.zeros_like(rms, dtype=np.uint8)

        # Ensure we have exactly num_samples
        if len(rms_normalized) > num_samples:
            rms_normalized = rms_normalized[:num_samples]
        elif len(rms_normalized) < num_samples:
            # Pad with zeros
            padding = np.zeros(num_samples - len(rms_normalized), dtype=np.uint8)
            rms_normalized = np.concatenate([rms_normalized, padding])

        return rms_normalized.tobytes()

    except Exception as e:
        logger.error(f"Error generating waveform for {audio_path}: {e}")
        return bytes(num_samples)


def generate_beat_grid(audio_path: str) -> List[Tuple[int, int, int]]:
    """Generate beat grid for PPOS tag.

    Args:
        audio_path: Path to audio file

    Returns:
        List of (beat_number, tempo, time_ms) tuples
    """
    try:
        import librosa
    except ImportError:
        logger.warning("librosa not installed. Cannot generate beat grid.")
        return []

    try:
        # Load audio
        y, sr = librosa.load(audio_path, sr=None, mono=True)

        # Beat tracking
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)

        # Convert beat frames to time in milliseconds
        beat_times = librosa.frames_to_time(beats, sr=sr)
        beat_times_ms = (beat_times * 1000).astype(int)

        # Create beat entries
        beats_list = []
        bpm_int = int(tempo * 100)  # BPM * 100

        for i, time_ms in enumerate(beat_times_ms):
            beats_list.append((i + 1, bpm_int, int(time_ms)))

        return beats_list

    except Exception as e:
        logger.error(f"Error generating beat grid for {audio_path}: {e}")
        return []


def generate_color_waveform(audio_path: str, num_columns: int = 1200) -> bytes:
    """Generate color waveform for PWV5 tag.

    Uses STFT to compute frequency bands and map to RGB colors.

    Args:
        audio_path: Path to audio file
        num_columns: Number of columns (default 1200)

    Returns:
        Color waveform data (3 bytes per column: RGB)
    """
    try:
        import librosa
    except ImportError:
        logger.warning("librosa not installed. Cannot generate color waveforms.")
        return bytes(num_columns * 3)

    try:
        # Load audio
        y, sr = librosa.load(audio_path, sr=None, mono=True)

        # STFT for frequency analysis
        n_fft = 2048
        hop_length = len(y) // num_columns

        # Compute spectrogram
        S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop_length))

        # Split into frequency bands (bass, mid, high)
        freq_bins = S.shape[0]
        bass_end = freq_bins // 4
        mid_end = freq_bins // 2

        bass = S[:bass_end, :]
        mid = S[bass_end:mid_end, :]
        high = S[mid_end:, :]

        # Compute energy per band per column
        bass_energy = np.mean(bass, axis=0)[:num_columns]
        mid_energy = np.mean(mid, axis=0)[:num_columns]
        high_energy = np.mean(high, axis=0)[:num_columns]

        # Normalize each band to 0-255
        def normalize(arr):
            if arr.max() > 0:
                return (arr / arr.max() * 255).astype(np.uint8)
            return np.zeros_like(arr, dtype=np.uint8)

        red = normalize(high_energy)    # High frequencies = Red
        green = normalize(mid_energy)   # Mid frequencies = Green
        blue = normalize(bass_energy)   # Bass = Blue

        # Build output (3 bytes per column)
        output = bytearray()
        for i in range(min(num_columns, len(red))):
            output += bytes([red[i], green[i], blue[i]])

        return bytes(output)

    except Exception as e:
        logger.error(f"Error generating color waveform for {audio_path}: {e}")
        return bytes(num_columns * 3)
