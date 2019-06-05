#!/usr/bin/env python

from mapi.mapi import MApi
from mapi.util.logger import log

if __name__ == '__main__':

    file_name = "./samples/marius.pst"

    log.info("PST example")
    with MApi(file_name) as mapi:
        pass
