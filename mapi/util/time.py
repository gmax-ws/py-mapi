#!/usr/bin/env python
from datetime import datetime

EPOCH_AS_FILETIME = 116444736000000000  # January 1, 1970 as MS file time
HUNDREDS_OF_NANOSECONDS = 10000000


def filetime2datetime(file_time):
    if file_time is None:
        return None
    else:
        return datetime.utcfromtimestamp((file_time - EPOCH_AS_FILETIME) / HUNDREDS_OF_NANOSECONDS)
