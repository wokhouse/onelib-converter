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
        Write djprofile.nxs file (CRITICAL: Required for rekordbox hardware!).

        Format based on onelib_and_devicelib reference:
        - Bytes 0-11: Header/magic (0x0061f9850000019bee8407c6)
        - Bytes 12-19: Reserved (8 bytes)
        - Bytes 20-27: Reserved/pointer (8 bytes)
        - Bytes 28-...: User name string (UTF-16LE or ASCII)
        - Rest: Padding to 160 bytes

        Args:
            settings: Optional dict with 'username' key
        """
        profile_path = self.pioneer_path / "djprofile.nxs"

        logger.info(f"Writing djprofile.nxs: {profile_path}")

        with open(profile_path, "wb") as f:
            # Header based on rekordbox export (exact bytes from reference)
            f.write(bytes.fromhex("0061f985"))  # Magic/part1
            f.write(bytes.fromhex("0000019b"))  # Part2
            f.write(bytes.fromhex("ee8407c6"))  # Part3
            f.write(b"\x00" * 8)  # Reserved (bytes 12-19)
            f.write(b"\x00" * 8)  # Reserved (bytes 20-27)
            # Offset marker at bytes 28-31 (from reference)
            f.write(bytes.fromhex("747d6a61"))  # "t}ja" - offset/pointer marker

            # Get system username to match rekordbox behavior
            # Try to get full name from system, fallback to username
            import subprocess
            import getpass
            try:
                # macOS: get full name from dscl
                system_user = getpass.getuser()
                result = subprocess.run(
                    ["dscl", ".", "-read", f"/Users/{system_user}", "RealName"],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                # Output format: "RealName: First Last" (may have leading space)
                if "RealName:" in result.stdout:
                    real_name = result.stdout.split("RealName:")[1].strip().split("\n")[0].strip()
                    username = real_name if real_name and real_name != "First Last" else None
                else:
                    username = None
            except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
                username = None

            # Fallback to settings or system username
            if not username and settings and "username" in settings:
                username = settings["username"]

            if not username:
                username = system_user

            # Write username as null-terminated ASCII string (max 32 bytes)
            username_bytes = username.encode("utf-8")[:32]
            f.write(username_bytes)
            f.write(b"\x00" * (32 - len(username_bytes)))  # Null padding

            # Pad to 160 bytes total (rekordbox standard size)
            current_size = f.tell()
            if current_size < 160:
                f.write(b"\x00" * (160 - current_size))

    def write_extracted_gcred(self) -> None:
        """
        Write extracted/gcred.dat file (CRITICAL: Required for rekordbox hardware!).

        This appears to be an encrypted credential/key file.
        Using the reference file's exact content.
        """
        extracted_dir = self.pioneer_path / "extracted"
        extracted_dir.mkdir(exist_ok=True)

        gcred_path = extracted_dir / "gcred.dat"

        logger.info(f"Writing gcred.dat: {gcred_path}")

        # Use the exact content from the reference file
        # This 66-byte file appears to be required for rekordbox validation
        reference_gcred = bytes.fromhex(
            "73575575344d314a6152737472736a51485051377775307671386d63342f4a5a"
            "5a436e345a594e5557625a75487641694459324d6f7938634e2f3173562b5a72"
            "0d0a"
        )

        with open(gcred_path, "wb") as f:
            f.write(reference_gcred)
