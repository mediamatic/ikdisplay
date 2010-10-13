"""
ikDisplay twistd plugin.
"""

from twisted.application.service import ServiceMaker

IkDisplay = ServiceMaker(
    "ikDisplayClient",
    "ikdisplay.client.tap",
    "ikDisplay client",
    "ikdisplayclient")
