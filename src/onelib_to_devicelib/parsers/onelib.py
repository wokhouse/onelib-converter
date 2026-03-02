"""
OneLibrary parser using pyrekordbox to read exportLibrary.db.
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

# Try to import pyrekordbox
try:
    from pyrekordbox.devicelib_plus import DeviceLibraryPlus
    PYREKORDBOX_AVAILABLE = True
except ImportError:
    PYREKORDBOX_AVAILABLE = False
    DeviceLibraryPlus = None

logger = logging.getLogger(__name__)


@dataclass
class Track:
    """Represents a single track from OneLibrary."""

    id: int
    title: str
    artist: str
    album: str
    genre: str
    bpm: float
    duration: float
    file_path: Path
    file_size: int
    bit_rate: int
    sample_rate: int
    cues: List[Dict[str, Any]] = field(default_factory=list)
    loops: List[Dict[str, Any]] = field(default_factory=list)
    hot_cues: List[Dict[str, Any]] = field(default_factory=list)
    beat_grid: Optional[List[float]] = None
    artwork_id: Optional[int] = None

    def has_analysis(self) -> bool:
        """Check if track has analysis data (waveforms, beat grid)."""
        return self.beat_grid is not None and len(self.beat_grid) > 0


@dataclass
class Playlist:
    """Represents a playlist from OneLibrary."""

    id: int
    name: str
    parent_id: Optional[int]
    track_ids: List[int] = field(default_factory=list)
    is_folder: bool = False


class OneLibraryParser:
    """
    Parser for OneLibrary export format (Device Library Plus).

    Uses pyrekordbox's DeviceLibraryPlus class to read the encrypted exportLibrary.db file.
    """

    def __init__(self, db_path: str | Path):
        """
        Initialize the OneLibrary parser.

        Args:
            db_path: Path to exportLibrary.db file
        """
        self.db_path = Path(db_path)

        if not PYREKORDBOX_AVAILABLE:
            raise ImportError(
                "pyrekordbox is required but not installed. "
                "Install it with: pip install pyrekordbox"
            )

        self.db: Optional[DeviceLibraryPlus] = None
        self.tracks: Dict[int, Track] = {}
        self.playlists: Dict[int, Playlist] = {}

    def parse(self) -> None:
        """
        Parse the OneLibrary database.

        Loads all tracks, playlists, cues, loops, and analysis data.
        """
        logger.info(f"Parsing OneLibrary database: {self.db_path}")

        # Open database using DeviceLibraryPlus (handles exportLibrary.db)
        self.db = DeviceLibraryPlus(self.db_path)

        # Load tracks
        self._load_tracks()

        # Load playlists
        self._load_playlists()

        # Load cues and loops
        self._load_cues_and_loops()

        logger.info(f"Parsed {len(self.tracks)} tracks and {len(self.playlists)} playlists")

    def _load_tracks(self) -> None:
        """Load all tracks from the database."""
        # Use pyrekordbox's get_content method
        for content in self.db.get_content():
            track = Track(
                id=content.content_id,
                title=content.title or "",
                artist=content.artist_name or "",
                album=content.album_name or "",
                genre=content.genre_name or "",
                bpm=(content.bpmx100 / 100) if content.bpmx100 else 0.0,
                duration=(content.length / 1000) if content.length else 0.0,  # Convert ms to seconds
                file_path=Path(content.path) if content.path else Path(),
                file_size=content.fileSize or 0,
                bit_rate=content.bitrate or 0,
                sample_rate=content.samplingRate or 0,
                artwork_id=None  # image_path is a string, not an ID
            )

            self.tracks[track.id] = track

    def _load_playlists(self) -> None:
        """Load all playlists and folders from the database."""
        # Use pyrekordbox's get_playlist method
        for playlist in self.db.get_playlist():
            # Check if this is a folder using the attribute field
            # attribute = 1 means folder (from PlaylistType.FOLDER)
            is_folder = playlist.attribute == 1 if hasattr(playlist, 'attribute') else False

            pl = Playlist(
                id=playlist.playlist_id,
                name=playlist.name or "",
                parent_id=playlist.playlist_id_parent,
                is_folder=is_folder
            )

            self.playlists[pl.id] = pl

        # Load playlist tracks
        for playlist_id, playlist in self.playlists.items():
            if playlist.is_folder:
                continue

            # Use get_playlist to get tracks (songs relationship)
            playlist_obj = self.db.get_playlist(playlist_id=playlist_id)
            if playlist_obj and hasattr(playlist_obj, 'songs'):
                for song in playlist_obj.songs:
                    playlist.track_ids.append(song.content_id)

    def _load_cues_and_loops(self) -> None:
        """Load hot cues, memory cues, and loops for all tracks."""
        # Use pyrekordbox's get_cue method
        for cue in self.db.get_cue():
            track_id = cue.content_id
            if track_id not in self.tracks:
                continue

            c = {
                "position": cue.position,
                "name": cue.name or "",
                "color": cue.color or 0xFFFFFF,
                "type": cue.type
            }

            # Type: 0 = Hot Cue, 1 = Memory Cue, 2 = Loop
            if cue.type == 2:
                self.tracks[track_id].loops.append(c)
            else:
                self.tracks[track_id].hot_cues.append(c)

    def get_tracks(self) -> List[Track]:
        """Get all parsed tracks."""
        return list(self.tracks.values())

    def get_track(self, track_id: int) -> Optional[Track]:
        """Get a specific track by ID."""
        return self.tracks.get(track_id)

    def get_playlists(self) -> List[Playlist]:
        """Get all parsed playlists."""
        return list(self.playlists.values())

    def get_playlist(self, playlist_id: int) -> Optional[Playlist]:
        """Get a specific playlist by ID."""
        return self.playlists.get(playlist_id)

    def close(self) -> None:
        """Close the database connection."""
        if self.db:
            self.db.close()
            self.db = None
