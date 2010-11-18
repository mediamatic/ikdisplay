"""
ikDisplay Aggregator twistd plugin.
"""

from twisted.application.service import ServiceMaker

IkDisplay = ServiceMaker(
    "ikDisplayAggregator",
    "ikdisplay.tap",
    "ikDisplay Aggregator",
    "ikdisplay-aggregator")
