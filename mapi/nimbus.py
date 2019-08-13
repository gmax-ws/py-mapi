def body_data(mapi):
    body = dict()
    body["text"] = mapi.body_text()
    body["html"] = mapi.body_html()
    body["rtf"] = "%s" % mapi.body_rtf()
    body["rtf_in_sync"] = mapi.rtf_in_sync()
    return body


def sender_data(mapi):
    sender = dict()
    sender["name"] = mapi.sender_name()
    sender["smtp_address"] = mapi.sender_smtp_address()
    sender["email_address"] = mapi.sender_email_address()
    return sender


def recipients_data(mapi):
    recipients = mapi.get_recipients()
    count = mapi.num_recipients()
    recipients_map = dict()
    recipients_map["count"] = count
    recipients_list = []
    for i in range(0, count):
        recipient_map = dict()
        recipient = recipients[i]
        recipient_map["name"] = recipient.get_recipient_display_name()
        recipient_map["smtp_address"] = recipient.get_smtp_address()
        recipient_map["email_address"] = recipient.get_email_address()
        recipients_list.append(recipient_map)
    recipients_map["recipients"] = recipients_list
    return recipients_map


def attachments_data(mapi):
    attachments = mapi.get_attachments()
    count = mapi.num_attachments()
    attachments_map = dict()
    attachments_map["has_attachments"] = mapi.has_attachments()
    attachments_map["count"] = count
    attachments_list = []
    for i in range(0, count):
        attachment_map = dict()
        attachment = attachments[i]
        attachment_map["id"] = attachment.get_attachment_number()
        attachment_map["mime"] = attachment.get_attachment_mime()
        attachment_map["name"] = attachment.get_display_name()
        attachment_map["type"] = attachment.get_object_type()
        attachment_map["method"] = attachment.get_attach_method()
        attachment_map["file_name"] = attachment.get_attachment_file_name()
        attachment_map["size"] = attachment.get_attachment_size()
        if attachment.is_attachment_msg():
            emb = attachment.get_embedded_attachment()
            if emb is not None:
                attachment_map["embedded"] = json_msg(emb)
        attachments_list.append(attachment_map)
    attachments_map["attachments"] = attachments_list
    return attachments_map


def iso_time(time):
    return None if time is None else time.isoformat()


def text_filter(data):
    if data is None:
        return None
    else:
        return data.replace("\u0000", "")


def json_msg(mapi):
    data = dict()
    data["id"] = mapi.message_id()
    data["class"] = mapi.message_class()
    data["submit_time"] = iso_time(mapi.message_submit_time())
    data["delivery_time"] = iso_time(mapi.message_delivery_time())
    data["receipt_time"] = iso_time(mapi.message_receipt_time())
    data["sender"] = sender_data(mapi)
    data["to"] = text_filter(mapi.display_to())
    data["cc"] = text_filter(mapi.display_cc())
    data["bcc"] = text_filter(mapi.display_bcc())
    data["subject"] = mapi.subject()
    data["body"] = body_data(mapi)
    data["recipients"] = recipients_data(mapi)
    data["attachments"] = attachments_data(mapi)
    return data
