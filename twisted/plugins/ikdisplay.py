"""
ikDisplay twistd plugin.
"""

from twisted.application.service import ServiceMaker

IkDisplay = ServiceMaker(
    "ikDisplay",
    "ikdisplay.tap",
    "ikDisplay service",
    "ikdisplay")
