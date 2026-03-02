"""
OneLib to DeviceLib Converter

Convert OneLibrary USB drives to dual-format (OneLibrary + Device Library)
for compatibility with older Pioneer DJ hardware.
"""

__version__ = "1.0.0"

from onelib_to_devicelib.convert import Converter

__all__ = ["Converter"]

