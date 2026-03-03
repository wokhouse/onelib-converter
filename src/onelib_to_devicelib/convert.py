"""
Main converter class for OneLibrary to Device Library conversion.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Optional
from tqdm import tqdm

from onelib_to_devicelib.parsers.onelib import OneLibraryParser
from onelib_to_devicelib.writers.pdb_v2 import PDBWriterV2, convert_tracks_to_pdb
from onelib_to_devicelib.writers.pdb import PDBWriter  # Keep for exportExt.pdb
from onelib_to_devicelib.writers.anlz import (
    ANLZGenerator,
    generate_mono_waveform,
    generate_beat_grid,
    generate_color_waveform,
)
from onelib_to_devicelib.writers.metadata_extractor import MetadataExtractor
from onelib_to_devicelib.utils.paths import get_pioneer_path, get_anlz_path_hash

logger = logging.getLogger(__name__)


class Converter:
    """
    Main converter that orchestrates the conversion from OneLibrary to Device Library.
    """

    def __init__(self, source_path: str | Path, output_path: Optional[str | Path] = None, pdb_version: str = 'v3'):
        """
        Initialize the converter.

        Args:
            source_path: Path to OneLibrary USB drive root
            output_path: Optional output path (defaults to source path for in-place conversion)
            pdb_version: PDB writer version to use ('v2' or 'v3', default: 'v3')
        """
        self.source_path = Path(source_path)
        self.output_path = Path(output_path) if output_path else self.source_path
        self.pdb_version = pdb_version

        # Validate source path
        if not self.source_path.exists():
            raise FileNotFoundError(f"Source path does not exist: {self.source_path}")

        self.pioneer_path = get_pioneer_path(self.source_path)
        if not self.pioneer_path.exists():
            raise FileNotFoundError(
                f"PIONEER directory not found. Is this a valid OneLibrary export? "
                f"Expected: {self.pioneer_path}"
            )

        # Initialize components
        self.parser = None
        self.pdb_writer = None

    def parse(self) -> OneLibraryParser:
        """
        Parse the OneLibrary export database.

        Returns:
            OneLibraryParser instance with parsed data
        """
        export_db = self.pioneer_path / "rekordbox" / "exportLibrary.db"

        if not export_db.exists():
            raise FileNotFoundError(
                f"exportLibrary.db not found at {export_db}"
            )

        self.parser = OneLibraryParser(export_db)
        self.parser.parse()

        return self.parser

    def convert(
        self,
        generate_waveforms: bool = False,
        analyze_missing: bool = False,
        copy_contents: bool = True,
    ) -> None:
        """
        Perform the conversion from OneLibrary to Device Library.

        Args:
            generate_waveforms: Whether to generate waveforms from audio files
            analyze_missing: Whether to analyze audio files with missing data
            copy_contents: Whether to copy Contents directory to output
        """
        # Parse source if not already done
        if self.parser is None:
            self.parse()

        # Create output directory structure
        self._create_output_structure(copy_contents)

        # Initialize old PDB writer (for exportExt.pdb only)
        self.pdb_writer = PDBWriter(self.output_path)

        # Track ANLZ paths for new PDB writer
        anlz_paths = {}

        # Convert tracks and generate ANLZ files
        tracks = self.parser.get_tracks()
        print(f"Converting {len(tracks)} tracks...")

        for track in tqdm(tracks, desc="Converting tracks"):
            # Try to copy existing ANLZ files from source FIRST
            # This preserves cue points!
            source_usbanlz = self.source_path / "PIONEER" / "USBANLZ"
            copied = False
            target_anlz_dir = None

            # Search for ANLZ files that belong to this track
            # by checking if the track title is in the DAT file
            track_title_utf16le = track.title.encode('utf-16le')

            for playlist_dir in source_usbanlz.glob("P*"):
                for hash_dir in playlist_dir.glob("*"):
                    if hash_dir.is_dir():
                        src_dat = hash_dir / "ANLZ0000.DAT"
                        if src_dat.exists():
                            # Check if this DAT file belongs to this track
                            # by searching for the track title in UTF-16LE encoding
                            try:
                                dat_content = src_dat.read_bytes()
                                if track_title_utf16le in dat_content:
                                    # Found matching ANLZ files - copy them!
                                    # Calculate target path
                                    target_anlz_dir = self.output_path / "PIONEER" / "USBANLZ" / playlist_dir.name / hash_dir.name
                                    target_anlz_dir.mkdir(parents=True, exist_ok=True)

                                    # Copy all ANLZ files
                                    import shutil
                                    for ext in ["DAT", "EXT", "2EX"]:
                                        src = hash_dir / f"ANLZ0000.{ext}"
                                        dst = target_anlz_dir / f"ANLZ0000.{ext}"
                                        if src.exists():
                                            shutil.copy2(src, dst)
                                    copied = True
                                    logger.info(f"Copied existing ANLZ files for {track.title} from {playlist_dir.name}/{hash_dir.name}")
                                    break
                            except Exception as e:
                                logger.warning(f"Error reading ANLZ file {src_dat}: {e}")
                                continue
                if copied:
                    break

            if copied:
                # Successfully copied - store path and skip generation
                anlz_rel = target_anlz_dir.relative_to(self.output_path / "PIONEER")
                anlz_paths[track.id] = f"/{anlz_rel}"
                # Add track to old PDB writer (for now, until we fully migrate)
                self.pdb_writer.add_track(track)
                continue

            # No existing ANLZ files found - need to generate
            # Get ANLZ directory for this track first (needed for new PDB writer)
            anlz_dir = self._get_anlz_dir(track)
            anlz_dir.mkdir(parents=True, exist_ok=True)

            # Store ANLZ path for new PDB writer
            # Convert to relative path from PIONEER root
            anlz_rel = anlz_dir.relative_to(self.output_path / "PIONEER")
            anlz_paths[track.id] = f"/{anlz_rel}"

            # Add track to old PDB writer (for now, until we fully migrate)
            self.pdb_writer.add_track(track)

            # Create ANLZ generator
            generator = ANLZGenerator(
                track_path=str(track.file_path),
                bpm=track.bpm,
                duration_ms=int(track.duration * 1000) if track.duration else 0
            )

            # Write DAT file (always required)
            generator.write_dat_file(anlz_dir / "ANLZ0000.DAT")

            # Generate waveforms and other files if requested
            if generate_waveforms or analyze_missing or not track.has_analysis():
                # Get audio file path
                audio_path = self.source_path / track.file_path

                if not audio_path.exists():
                    logger.warning(f"Audio file not found: {audio_path}")
                    # Write minimal ANLZ files
                    generator.write_ext_file(
                        anlz_dir / "ANLZ0000.EXT",
                        bytes(400)  # Placeholder waveform
                    )
                    generator.write_2ex_file(
                        anlz_dir / "ANLZ0000.2EX",
                        bytes(1200 * 3),  # Placeholder color waveform
                        [],  # No beat grid
                        []   # No cues
                    )
                    continue

                try:
                    # Generate waveform
                    waveform = generate_mono_waveform(str(audio_path))
                    generator.write_ext_file(anlz_dir / "ANLZ0000.EXT", waveform)

                    # Generate beat grid
                    beats = generate_beat_grid(str(audio_path))

                    # Generate color waveform
                    color_waveform = generate_color_waveform(str(audio_path))

                    # Convert cues to format expected by 2EX
                    cues = []
                    for cue in track.hot_cues:
                        cues.append({
                            'id': cue.get('position_ms', 0) // 1000,  # Simple ID
                            'position_ms': int(cue.get('position', 0)),
                            'type': cue.get('type', 0)
                        })

                    # Write 2EX file
                    generator.write_2ex_file(
                        anlz_dir / "ANLZ0000.2EX",
                        color_waveform,
                        beats,
                        cues
                    )

                except Exception as e:
                    logger.error(f"Error generating ANLZ for {track.title}: {e}")
                    # Write minimal files
                    generator.write_ext_file(
                        anlz_dir / "ANLZ0000.EXT",
                        bytes(400)
                    )
                    generator.write_2ex_file(
                        anlz_dir / "ANLZ0000.2EX",
                        bytes(1200 * 3),
                        [],
                        []
                    )
            else:
                # Use existing analysis data (copy from source)
                self._copy_existing_anlz(track, anlz_dir)

            # Get ANLZ directory for this track
            anlz_dir = self._get_anlz_dir(track)
            anlz_dir.mkdir(parents=True, exist_ok=True)

            # Create ANLZ generator
            generator = ANLZGenerator(
                track_path=str(track.file_path),
                bpm=track.bpm,
                duration_ms=int(track.duration * 1000) if track.duration else 0
            )

            # Write DAT file (only if not already copied)
            generator.write_dat_file(anlz_dir / "ANLZ0000.DAT")

            # Generate waveforms and other files if requested
            if generate_waveforms or analyze_missing or not track.has_analysis():
                # Get audio file path
                audio_path = self.source_path / track.file_path

                if not audio_path.exists():
                    logger.warning(f"Audio file not found: {audio_path}")
                    # Write minimal ANLZ files
                    generator.write_ext_file(
                        anlz_dir / "ANLZ0000.EXT",
                        bytes(400)  # Placeholder waveform
                    )
                    generator.write_2ex_file(
                        anlz_dir / "ANLZ0000.2EX",
                        bytes(1200 * 3),  # Placeholder color waveform
                        [],  # No beat grid
                        []   # No cues
                    )
                    continue

                try:
                    # Generate waveform
                    waveform = generate_mono_waveform(str(audio_path))
                    generator.write_ext_file(anlz_dir / "ANLZ0000.EXT", waveform)

                    # Generate beat grid
                    beats = generate_beat_grid(str(audio_path))

                    # Generate color waveform
                    color_waveform = generate_color_waveform(str(audio_path))

                    # Convert cues to format expected by 2EX
                    cues = []
                    for cue in track.hot_cues:
                        cues.append({
                            'id': cue.get('position_ms', 0) // 1000,  # Simple ID
                            'position_ms': int(cue.get('position', 0)),
                            'type': cue.get('type', 0)
                        })

                    # Write 2EX file
                    generator.write_2ex_file(
                        anlz_dir / "ANLZ0000.2EX",
                        color_waveform,
                        beats,
                        cues
                    )

                except Exception as e:
                    logger.error(f"Error generating ANLZ for {track.title}: {e}")
                    # Write minimal files
                    generator.write_ext_file(
                        anlz_dir / "ANLZ0000.EXT",
                        bytes(400)
                    )
                    generator.write_2ex_file(
                        anlz_dir / "ANLZ0000.2EX",
                        bytes(1200 * 3),
                        [],
                        []
                    )
            else:
                # Use existing analysis data (copy from source)
                self._copy_existing_anlz(track, anlz_dir)

        # Convert playlists
        playlists = self.parser.get_playlists()
        print(f"Converting {len(playlists)} playlists...")

        for playlist in tqdm(playlists, desc="Converting playlists"):
            self.pdb_writer.add_playlist(playlist)

        # Write PDB files
        print("Writing export.pdb and exportExt.pdb...")

        # Use appropriate PDB writer based on version
        if self.pdb_version == 'minimal':
            print("  Using minimal PDB format (Tracks table only)...")
            from onelib_to_devicelib.writers.pdb_minimal import PDBWriterMinimal

            writer = PDBWriterMinimal(self.output_path)

            # Add tracks
            print("  Adding tracks to PDB...")
            for track in tracks:
                writer.add_track(track)

            file_size = writer.finalize()
            stats = writer.get_stats()
            print(f"  Generated export.pdb: {file_size:,} bytes ({stats['total_pages']} pages)")

        elif self.pdb_version == 'v3':
            print("  Using REX-compliant PDB format (PDBWriterV3)...")
            from onelib_to_devicelib.writers.pdb_v3 import PDBWriterV3

            # Extract metadata and assign IDs
            print("  Extracting metadata (genres, artists, albums)...")
            extractor = MetadataExtractor()
            extractor.extract_from_tracks(tracks)

            # Assign IDs to all tracks
            for track in tracks:
                extractor.assign_track_ids(track)

            # Print stats
            stats = extractor.get_stats()
            print(f"    Found: {stats['genres']} genres, {stats['artists']} artists, "
                  f"{stats['albums']} albums, {stats['labels']} labels, {stats['keys']} keys")

            # Initialize PDB writer v3
            writer_v3 = PDBWriterV3(self.output_path)

            # Populate metadata tables first
            print("  Populating metadata tables...")
            for genre_name, genre_id in extractor.genres.items():
                writer_v3.add_genre(genre_id, genre_name)

            for artist_name, artist_id in extractor.artists.items():
                writer_v3.add_artist(artist_id, artist_name)

            for album_name, album_id in extractor.albums.items():
                # Get artist ID for this album
                album_artist_id = extractor.get_album_artist_id(album_name)
                writer_v3.add_album(album_id, album_name, album_artist_id)

            for label_name, label_id in extractor.labels.items():
                writer_v3.add_label(label_id, label_name)

            for key_name, key_id in extractor.keys.items():
                writer_v3.add_key(key_id, key_name)

            # Add colors (fixed set of rekordbox colors)
            rekordbox_colors = [
                (0, 'None', 0x000000),
                (1, 'Pink', 0xFF1493),
                (2, 'Red', 0xFF0000),
                (3, 'Orange', 0xFF7F00),
                (4, 'Yellow', 0xFFFF00),
                (5, 'Lime', 0xBFFF00),
                (6, 'Green', 0x00FF00),
                (7, 'Turquoise', 0x00FFFF),
                (8, 'Cyan', 0x00BFFF),
                (9, 'Blue', 0x0000FF),
                (10, 'Purple', 0x9D00FF),
                (11, 'Magenta', 0xFF00FF),
            ]
            for color_id, name, rgb in rekordbox_colors:
                writer_v3.add_color(color_id, name, rgb)

            # Add playlists and playlist entries
            print("  Adding playlists to PDB...")
            for playlist in playlists:
                # Add playlist/folder to PlaylistTree
                writer_v3.add_playlist(playlist)

                # Add playlist entries for tracks (if not a folder)
                if not playlist.is_folder and playlist.track_ids:
                    for seq_no, track_id in enumerate(playlist.track_ids):
                        writer_v3.add_playlist_entry(track_id, playlist.id, seq_no)

            # Add tracks (now with IDs assigned)
            print("  Adding tracks to PDB...")
            for track in tracks:
                writer_v3.add_track(track)

            file_size = writer_v3.finalize()
            stats = writer_v3.get_stats()
            print(f"  Generated export.pdb: {file_size:,} bytes ({stats['total_pages']} pages)")

            # Print table statistics
            print("  Table statistics:")
            for table_name, table_stats in stats['tables'].items():
                if table_stats['num_pages'] > 0:
                    print(f"    {table_name}: {table_stats['num_pages']} pages, "
                          f"{table_stats['total_rows']} rows")
        else:
            # Use V2 writer
            print("  Using enhanced PDB format (PDBWriterV2)...")
            try:
                convert_tracks_to_pdb(tracks, self.output_path, anlz_paths)
            except Exception as e:
                logger.warning(f"New PDB writer failed: {e}, falling back to old writer")
                self.pdb_writer.write()

        # Write exportExt.pdb using old writer
        self.pdb_writer.write_export_ext_pdb()

        # Generate supporting files
        print("Generating supporting files...")
        self._generate_supporting_files()

        print("Conversion complete!")

    def _get_anlz_dir(self, track) -> Path:
        """Get the ANLZ directory for a track."""
        # Generate hash from track path
        path_hash = get_anlz_path_hash(track.file_path)

        # Use playlist ID 001 for now
        anlz_dir = (
            self.output_path
            / "PIONEER"
            / "USBANLZ"
            / f"P001"
            / path_hash
        )

        return anlz_dir

    def _copy_existing_anlz(self, track, target_dir: Path) -> None:
        """Copy existing ANLZ files from source to target."""
        # Find source ANLZ files
        source_usbanlz = self.source_path / "PIONEER" / "USBANLZ"

        # Search for matching ANLZ files by comparing track paths
        for playlist_dir in source_usbanlz.glob("P*"):
            for hash_dir in playlist_dir.glob("*"):
                if hash_dir.is_dir():
                    dat_file = hash_dir / "ANLZ0000.DAT"
                    if dat_file.exists():
                        # Copy all ANLZ files
                        for ext in ["DAT", "EXT", "2EX"]:
                            src = hash_dir / f"ANLZ0000.{ext}"
                            dst = target_dir / f"ANLZ0000.{ext}"
                            if src.exists():
                                import shutil
                                shutil.copy2(src, dst)
                        logger.debug(f"Copied existing ANLZ files for {track.title}")
                        return

        # If not found, generate minimal files
        logger.warning(f"No existing ANLZ files found for {track.title}, generating minimal ones")
        generator = ANLZGenerator(
            track_path=str(track.file_path),
            bpm=track.bpm,
            duration_ms=int(track.duration * 1000) if track.duration else 0
        )
        generator.write_dat_file(target_dir / "ANLZ0000.DAT")
        generator.write_ext_file(target_dir / "ANLZ0000.EXT", bytes(400))
        generator.write_2ex_file(
            target_dir / "ANLZ0000.2EX",
            bytes(1200 * 3),
            [],
            []
        )

    def _create_output_structure(self, copy_contents: bool) -> None:
        """Create the output directory structure."""
        # Create PIONEER directory
        pioneer_output = get_pioneer_path(self.output_path)
        pioneer_output.mkdir(parents=True, exist_ok=True)

        # Create required subdirectories
        (pioneer_output / "rekordbox").mkdir(exist_ok=True)
        (pioneer_output / "USBANLZ").mkdir(exist_ok=True)
        (pioneer_output / "Artwork").mkdir(exist_ok=True)

        # Copy Contents directory if requested
        if copy_contents and self.source_path != self.output_path:
            contents_source = self.source_path / "Contents"
            contents_output = self.output_path / "Contents"

            if contents_source.exists():
                print(f"Copying Contents directory...")
                shutil.copytree(contents_source, contents_output)

    def _generate_supporting_files(self) -> None:
        """Generate supporting files (DEVSETTING.DAT, etc.)."""
        from onelib_to_devicelib.writers.metadata import MetadataWriter

        metadata_writer = MetadataWriter(self.output_path)
        metadata_writer.write_devsetting()
        metadata_writer.write_device_lib_backup()
