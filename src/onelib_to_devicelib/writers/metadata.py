"""
Metadata file writers for DEVSETTING.DAT, DeviceLibBackup, and other supporting files.
"""

import json
import logging
import struct
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


class MetadataWriter:
    """
    Writer for supporting metadata files.

    Generates:
    - DEVSETTING.DAT - Device settings
    - DeviceLibBackup/rbDevLibBaInfo_*.json - Device backup info
    - djprofile.nxs - DJ performance profile (optional)
    """

    def __init__(self, output_path: str | Path):
        """
        Initialize the metadata writer.

        Args:
            output_path: Path to output directory
        """
        self.output_path = Path(output_path)
        self.pioneer_path = self.output_path / "PIONEER"
        self.pioneer_path.mkdir(parents=True, exist_ok=True)

    def write_devsetting(self) -> None:
        """
        Write DEVSETTING.DAT file.

        This file contains device-specific settings for Rekordbox export.
        """
        devsetting_path = self.pioneer_path / "DEVSETTING.DAT"

        logger.info(f"Writing DEVSETTING.DAT: {devsetting_path}")

        with open(devsetting_path, "wb") as f:
            # Magic header: "PIONEER DJ"
            f.write(b"\x60\x00\x00\x00")
            f.write(b"PIONEER DJ")
            f.write(b"\x00" * 9)  # Padding

            # Rekordbox identifier
            f.write(b"\x00" * 16)
            f.write(b"rekordbox")
            f.write(b"\x00" * 9)

            # Version (7.2.9)
            f.write(b"7.2.9")
            f.write(b"\x00" * 7)

            # Additional settings (placeholder)
            # Real implementation would include actual device settings
            f.write(b"\x20\x00\x00\x00")  # Settings flag
            f.write(b"\x78\x56\x34\x12")  # Endianness marker

            # Reserved
            f.write(b"\x01\x00\x00\x00")
            f.write(b"\x01" * 16)

            # More settings
            f.write(b"\x00" * 20)

            # Unknown ending
            f.write(b"\xe1\x98")
            f.write(b"\x00" * 6)

    def write_device_lib_backup(self) -> None:
        """
        Write DeviceLibBackup/rbDevLibBaInfo_*.json file.

        This contains the device library backup information with UUID.
        """
        backup_dir = self.pioneer_path / "DeviceLibBackup"
        backup_dir.mkdir(exist_ok=True)

        # Generate UUID for this export
        export_uuid = uuid.uuid4().hex

        # Create filename with timestamp
        import time
        timestamp = int(time.time())
        filename = f"rbDevLibBaInfo_{timestamp}.json"
        backup_path = backup_dir / filename

        logger.info(f"Writing DeviceLibBackup: {backup_path}")

        # Create JSON structure
        backup_data = {
            "uuid": export_uuid,
            "info": []  # Would contain device-specific info
        }

        with open(backup_path, "w") as f:
            json.dump(backup_data, f, indent=2)

    def write_djprofile(self, settings: dict | None = None) -> None:
        """
        Write djprofile.nxs file (optional).

        Args:
            settings: Optional DJ performance settings
        """
        profile_path = self.pioneer_path / "djprofile.nxs"

        logger.info(f"Writing djprofile.nxs: {profile_path}")

        # This is a binary format - structure not fully documented
        # Writing minimal placeholder

        with open(profile_path, "wb") as f:
            # Placeholder header
            f.write(b"NXS\x00")  # Magic
            f.write(struct.pack("<I", 1))  # Version

            if settings:
                # Would write actual DJ settings here
                pass

    def write_extracted_gcred(self) -> None:
        """
        Write extracted/gcred.dat file.

        Purpose of this file is not well understood.
        Writing minimal placeholder.
        """
        extracted_dir = self.pioneer_path / "extracted"
        extracted_dir.mkdir(exist_ok=True)

        gcred_path = extracted_dir / "gcred.dat"

        logger.info(f"Writing gcred.dat: {gcred_path}")

        # This file appears to be ~66 bytes
        # Exact purpose unknown
        with open(gcred_path, "wb") as f:
            f.write(b"\x00" * 66)
