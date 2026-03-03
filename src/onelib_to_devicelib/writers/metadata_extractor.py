"""
Metadata Extractor

Extracts and assigns IDs for genres, artists, albums, labels, and keys
from a collection of tracks.
"""

from typing import Dict, List


class MetadataExtractor:
    """Extracts metadata from tracks and assigns IDs.

    This class processes a collection of tracks to extract unique values
    for genres, artists, albums, labels, and keys, then assigns sequential
    IDs to each unique value.
    """

    # Rekordbox standard keys
    REKORDBOX_KEYS = [
        'C maj', 'Db maj', 'D maj', 'Eb maj', 'E maj', 'F maj',
        'Gb maj', 'G maj', 'Ab maj', 'A maj', 'Bb maj', 'B maj',
        'C min', 'C# min', 'D min', 'D# min', 'E min', 'F min',
        'F# min', 'G min', 'G# min', 'A min', 'A# min', 'B min'
    ]

    def __init__(self):
        """Initialize metadata extractor with empty dictionaries."""
        self.genres: Dict[str, int] = {}
        self.artists: Dict[str, int] = {}
        self.albums: Dict[str, int] = {}
        self.album_artists: Dict[str, int] = {}  # Album -> Artist ID mapping
        self.labels: Dict[str, int] = {}
        self.keys: Dict[str, int] = {}

        # ID counters
        self._next_genre_id = 1
        self._next_artist_id = 1
        self._next_album_id = 1
        self._next_label_id = 1
        self._next_key_id = 1

    def extract_from_tracks(self, tracks: List) -> None:
        """Extract unique metadata from tracks.

        Args:
            tracks: List of Track objects from OneLibraryParser
        """
        for track in tracks:
            # Extract genre
            if track.genre and track.genre not in self.genres:
                self.genres[track.genre] = self._next_genre_id
                self._next_genre_id += 1

            # Extract artist
            if track.artist and track.artist not in self.artists:
                self.artists[track.artist] = self._next_artist_id
                self._next_artist_id += 1

            # Extract album
            if track.album and track.album not in self.albums:
                self.albums[track.album] = self._next_album_id

                # Store album-artist relationship
                if track.artist:
                    # Album gets the artist ID from this track
                    artist_id = self.artists.get(track.artist, 0)
                    self.album_artists[track.album] = artist_id
                else:
                    self.album_artists[track.album] = 0

                self._next_album_id += 1

            # Extract label (if available)
            if hasattr(track, 'label') and track.label and track.label not in self.labels:
                self.labels[track.label] = self._next_label_id
                self._next_label_id += 1

        # Initialize standard keys
        for key_name in self.REKORDBOX_KEYS:
            if key_name not in self.keys:
                self.keys[key_name] = self._next_key_id
                self._next_key_id += 1

    def assign_track_ids(self, track) -> None:
        """Assign metadata IDs to a track.

        Args:
            track: Track object to modify (sets genre_id, artist_id, album_id, key_id)
        """
        # Assign genre ID
        if track.genre and track.genre in self.genres:
            track.genre_id = self.genres[track.genre]
        else:
            track.genre_id = 0

        # Assign artist ID
        if track.artist and track.artist in self.artists:
            track.artist_id = self.artists[track.artist]
        else:
            track.artist_id = 0

        # Assign album ID
        if track.album and track.album in self.albums:
            track.album_id = self.albums[track.album]
        else:
            track.album_id = 0

        # Assign key ID (based on track's key text)
        if hasattr(track, 'key') and track.key:
            # Try to match key text to standard keys
            key_name = self._normalize_key(track.key)
            if key_name in self.keys:
                track.key_id = self.keys[key_name]
            else:
                track.key_id = 0
        else:
            track.key_id = 0

        # Assign label ID (if available)
        if hasattr(track, 'label') and track.label and track.label in self.labels:
            track.label_id = self.labels[track.label]
        else:
            if hasattr(track, 'label_id'):
                track.label_id = 0

    def get_album_artist_id(self, album_name: str) -> int:
        """Get the artist ID for an album.

        Args:
            album_name: Name of the album

        Returns:
            Artist ID (0 if no artist associated)
        """
        return self.album_artists.get(album_name, 0)

    def _normalize_key(self, key: str) -> str:
        """Normalize key text to rekordbox format.

        Args:
            key: Key text from track

        Returns:
            Normalized key name (e.g., "C maj", "A min")
        """
        if not key:
            return None

        key_lower = key.lower().strip()

        # Handle various key notations
        # Minor keys
        if 'm' in key_lower and 'maj' not in key_lower:
            # It's a minor key
            base = key_lower.replace('m', '').replace(' ', '').strip()
            # Convert sharps/flats
            base = base.replace('db', 'Db').replace('eb', 'Eb').replace(
                'gb', 'Gb').replace('ab', 'Ab').replace('bb', 'Bb')
            base = base.replace('c#', 'C#').replace('d#', 'D#').replace(
                'f#', 'F#').replace('g#', 'G#').replace('a#', 'A#')
            base = base.capitalize()
            return f"{base} min"
        else:
            # It's a major key
            base = key_lower.replace('maj', '').replace(' ', '').strip()
            # Convert sharps/flats
            base = base.replace('db', 'Db').replace('eb', 'Eb').replace(
                'gb', 'Gb').replace('ab', 'Ab').replace('bb', 'Bb')
            base = base.replace('c#', 'C#').replace('d#', 'D#').replace(
                'f#', 'F#').replace('g#', 'G#').replace('a#', 'A#')
            base = base.capitalize()
            return f"{base} maj"
