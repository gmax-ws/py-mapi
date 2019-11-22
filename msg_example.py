#!/usr/bin/env python

import json

from mapi.mapi import MApi
from mapi.nimbus import *
from mapi.util.logger import log
from mapi.util.timetracker import *


def extract_attachments(mapi, location="./"):
    attachments = mapi.get_attachments()
    for i in range(0, mapi.num_attachments()):
        log.info("attachment %d => %s %s %s" %
                 (i, attachments[i].is_attachment_object(),
                  attachments[i].get_attachment_mime(),
                  attachments[i].get_object_type()))
        attachment_name = attachments[i].get_attachment_file_name()
        if attachment_name is None:
            log.warn("attachment %d unknown attachment name!" % i)
            attachment_name = "unknown-%d" % i
        data = attachments[i].get_attachment()
        if data is None:
            log.warn("attachment %d found no data!" % i)
        else:
            with open(location + attachment_name, "wb") as f:
                written = f.write(data)
                log.info("attachment: %d name: %s content id: %s size: %s" %
                         (attachments[i].get_attachment_number(),
                          attachment_name,
                          attachments[i].get_display_name(),
                          written))


if __name__ == '__main__':
    import logging
    log.setLevel(logging.INFO)

    file_name = "./samples/test2.msg"

    with TimeTracker() as t:
        with MApi(file_name) as mapi:
            # extract_attachments(mapi, "/home/marius/attachments/")
            #
            # print(mapi.rtf_as_text())
            # r = mapi.body_rtf()
            # if r is not None:
            #     with open("/home/marius/test.rtf", "wb") as f:
            #         f.write(r)
            #     with open("/home/marius/test.html", "wt") as f:
            #         f.write(mapi.body_html())
            #     with open("/home/marius/test.txt", "wt") as f:
            #         f.write(mapi.body_text())

            json_data = json.dumps(json_msg(mapi), sort_keys=False, indent=2)
            log.info(json_data)
            parsed_json = json.loads(json_data)
            log.info("=" * 80)
            log.info(parsed_json)
            log.info("=" * 80)

    log.info("Process time (seconds): %5.3f" % t.elapsed)
