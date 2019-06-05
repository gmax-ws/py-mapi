#!/usr/bin/env python

from mapi.mapi import MApi
from mapi.util.logger import log
from mapi.util.timetracker import *

if __name__ == '__main__':

    file_name = "./samples/cot.msg"

    with TimeTracker() as t:
        with MApi(file_name) as mapi:
            log.info("Message class: %s" % mapi.message_class())
            log.info("Message delivery time: %s" % mapi.message_delivery_time())
            log.info("From: %s <%s>" % (mapi.sender_name(),
                                        mapi.sender_smtp_address()))
            log.info("EMAIL address: %s" % mapi.sender_email_address())
            log.info("Subject: %s" % mapi.subject())
            log.info("Body Content Id: %s" % mapi.body_content_id())
            log.info("Body: %s" % mapi.body_text())
            # log.info("Body HTML: %s" % mapi.body_html())
            if mapi.rtf_in_sync() is not None:
                log.info("RTF in sync: %d" % mapi.rtf_in_sync())
            log.info("Body RTF: %s" % mapi.body_rtf())

            print(mapi.rtf_as_text())
            r = mapi.body_rtf()
            if r is not None:
                with open("/home/marius/test.rtf", "wb") as f:
                    f.write(r)
                with open("/home/marius/test.html", "wt") as f:
                    f.write(mapi.body_html())
                with open("/home/marius/test.txt", "wt") as f:
                    f.write(mapi.body_text())

            log.info("Has attachments: %s" % mapi.has_attachments())
            log.info("recipients: %d attachments: %d" %
                     (mapi.num_recipients(), mapi.num_attachments()))
            recipients = mapi.get_recipients()
            for i in range(0, mapi.num_recipients()):
                log.info("name: %s address: %s " %
                         (recipients[i].get_recipient_display_name(),
                          recipients[i].get_smtp_address()))
                log.info("email address: %s" % recipients[i].get_email_address())
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
                att = attachments[i].get_attachment()
                emb = attachments[i].get_embedded_attachment()
                if emb is not None:
                    print(emb.message_class())
                    print(emb.subject())
                    print(emb.num_recipients(), emb.num_attachments())
                    print(emb.recipients[0].get_display_name(),
                          emb.recipients[0].get_email_address())
                if att is None:
                    log.warn("attachment %d found no data!" % i)
                else:
                    with open("/home/marius/attachments/" + attachment_name, "wb") as f:
                        written = f.write(att)
                        log.info("attachment: %d name: %s content id: %s size: %s" %
                                 (attachments[i].get_attachment_number(),
                                  attachment_name,
                                  attachments[i].get_display_name(),
                                  written))

    log.info("Process time (seconds): %5.3f" % t.elapsed)
