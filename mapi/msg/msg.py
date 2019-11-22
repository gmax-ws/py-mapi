from mapi.cfb.cfb import *
from mapi.msg.mapi_tags import *
from mapi.msg.mapi_types import *
from mapi.rtf.rtf import decompress
from mapi.rtf.rtf_decoder import *
from mapi.util.crc32 import *
from mapi.util.decoder import *
from mapi.util.logger import log
from mapi.util.time import *

RTF_MIN_SIZE = 16
MSG_PROPERTY_SIZE = 16

STORE_OBJECT = 0x00000001
ADDRESS_BOOK_object = 0x00000002
ADDRESS_BOOK_CONTAINER = 0x00000004
MESSAGE_OBJECT = 0x00000005
MAIL_USER = 0x00000006
ATTACHMENT_OBJECT = 0x00000007
DISTRIBUTION_LIST = 0x00000008

BASE_STREAM_ID = 0x1000
MIN_ID = 0x8000
MAX_ID = 0xFFFE

MSG_NAMEID = "__nameid_version1.0"
MSG_RECIP = "__recip_version1.0"
MSG_ATTACH = "__attach_version1.0"
MSG_SUBSTG = "__substg1.0_"
MSG_PROPS = "__properties_version1.0"
MSG_EMBEDDED = "__substg1.0_3701000D"


class MsgNamedProperties:
    __slots__ = ['cfb', 'props', 'guids', 'entry', 'string']

    def __init__(self, cfb):
        self.cfb = cfb
        self.props = cfb.cfb_root.select_entry_by_name(MSG_NAMEID)[0]

        name = MsgStorage.property_name(PidTagNameidStreamGuid, PtypBinary)
        _data = cfb.read_stream(self.props, name)
        self.guids = [_data[i:i + 16] for i in range(0, len(_data), 16)]

        name = MsgStorage.property_name(PidTagNameidStreamEntry, PtypBinary)
        _data = cfb.read_stream(self.props, name)
        self.entry = [(uint32(_data[i:i + 4]), uint16(_data[i + 4:i + 6]), uint16(_data[i + 6:i + 8]))
                      for i in range(0, len(_data), 8)]

        name = MsgStorage.property_name(PidTagNameidStreamString, PtypBinary)
        self.string = cfb.read_stream(self.props, name)

        # print(self.property_name(0x8001), self.mapping(0x8001, 0x0102), self.property_guid(0x8001))
        # print(self.property_name(0x800a), self.mapping(0x800a, 0x0102), self.property_guid(0x800a))
        # print(self.property_name(0x800e), self.mapping(0x800e, 0x0102), self.property_guid(0x800e))

    def mapping(self, _id, typ=PtypBinary):
        ent = self._get_entry(_id)
        return self._compute(ent, typ)

    def property_name(self, _id):
        ent = self._get_entry(_id)
        if self._property_kind(ent) == 0:
            name = self._name_identifier(ent)
        else:
            name = self._get_name_utf16(ent)
        return name

    def property_guid(self, _id):
        ent = self._get_entry(_id)
        return self._guid(self._guid_index(ent))

    def _get_entry(self, _id):
        assert (MIN_ID <= _id <= MAX_ID)
        index = _id - MIN_ID
        assert (0 <= index < len(self.entry))
        return self.entry[index]

    def _compute(self, ent, typ):
        if self._property_kind(ent) == 0:
            name = self._name_identifier(ent)
            stream_id = BASE_STREAM_ID + (name ^ (self._guid_index(ent) << 1)) % 0x1F
        else:
            name = crc32(self._get_name(ent))
            stream_id = BASE_STREAM_ID + (name ^ ((self._guid_index(ent) << 1) | 1)) % 0x1F
        return stream_id, "%s%04X%04X" % (MSG_SUBSTG, stream_id, typ)

    def _guid(self, i):
        return guid(self.guids[i])

    def _get_name(self, ent):
        offset = self._string_offset(ent)
        size = uint32(self.string[offset:offset + 4])
        return self.string[offset + 4:offset + 4 + size]

    def _get_name_utf16(self, ent):
        return utf16(self._get_name(ent))

    @staticmethod
    def _property_kind(ent):
        return ent[1] & 0x0001

    @staticmethod
    def _property_index(ent):
        return ent[2]

    @staticmethod
    def _guid_index(ent):
        return ent[1] >> 1

    @staticmethod
    def _name_identifier(ent):
        return ent[0]

    @staticmethod
    def _string_offset(ent):
        return ent[0]

    @staticmethod
    def _entry(ent):
        return ent[0], ent[1] >> 1, ent[1] & 0x0001, ent[2]


class MsgProperties:
    __slots__ = ['name', 'cfb', 'header', 'properties']

    def __init__(self, cfb, storage, name):
        self.name = name
        self.cfb = cfb
        props = self.cfb.read_stream(storage, MSG_PROPS)
        assert (props is not None)
        self._header(name, props)
        properties = props[len(self.header):]
        properties_list = [properties[i:i + MSG_PROPERTY_SIZE]
                           for i in range(0, len(properties), MSG_PROPERTY_SIZE)]
        self.properties = [self._property(prop) for prop in properties_list]
        self.debug(0)

    def debug(self, b):
        if b:
            print(self.name)
            for prop in self.properties:
                print(hex(prop[0]), hex(prop[1]), hex(prop[2]), prop[3])

    def _header(self, name, props):
        if name.startswith(ROOT_ENTRY):
            self.header = props[0:32]
        else:
            if name == MSG_EMBEDDED:
                self.header = props[0:24]
            elif name.startswith(MSG_RECIP) or name.startswith(MSG_ATTACH):
                self.header = props[0:8]

    def next_recipient_id(self):
        assert (len(self.header) >= 24)
        return uint32(self.header[8:12])

    def next_attachment_id(self):
        assert (len(self.header) >= 24)
        return uint32(self.header[12:16])

    def num_recipients(self):
        assert (len(self.header) >= 24)
        return uint32(self.header[16:20])

    def num_attachments(self):
        assert (len(self.header) >= 24)
        return uint32(self.header[20:24])

    def get_property(self, tag, typ):
        for prop in self.properties:
            if prop[0] == typ and prop[1] == tag:
                return prop[2], int32(prop[3][0:4]), uint32(prop[3][4:8])
        return None, None, None

    def get_property_bool(self, tag, typ):
        for prop in self.properties:
            if prop[0] == typ and prop[1] == tag:
                return prop[2], uint8(prop[3][0:1])
        return None, None

    def get_property_int64(self, tag, typ):
        for prop in self.properties:
            if prop[0] == typ and prop[1] == tag:
                return prop[2], int64(prop[3][0:8])
        return None, None

    def get_property_float(self, tag, typ):
        for prop in self.properties:
            if prop[0] == typ and prop[1] == tag:
                return prop[2], float(prop[3][0:4]), uint32(prop[3][4:8])
        return None, None, None

    def get_property_long(self, tag, typ):
        for prop in self.properties:
            if prop[0] == typ and prop[1] == tag:
                return prop[2], uint64(prop[3][0:8])
        return None, None, None

    @staticmethod
    def _property(prop):
        # property_type, property_tag, flags, value
        return uint16(prop[0:2]), uint16(prop[2:4]), uint32(prop[4:8]), prop[8:]


class MsgStorage:
    __slots__ = ['cfb', 'data', 'props']

    def __init__(self, cfb, data):
        self.cfb = cfb
        self.data = data
        name = data.directory_entry_name()
        if name.startswith(MSG_NAMEID):
            self.props = None
        else:
            self.props = MsgProperties(cfb, data, name)

    def stream(self, tag, typ):
        return self._read_stream(self.data, tag, typ)

    def find(self, tag, typ):
        return self._find_stream(self.data, tag, typ)

    def _read_stream(self, root, tag, typ):
        prop_name = self.property_name(tag, typ)
        return self.cfb.read_stream(root, prop_name)

    def _find_stream(self, root, tag, typ):
        prop_name = self.property_name(tag, typ)
        return self.cfb.find_stream(root, prop_name)

    def get_display_name(self):
        _data = self.stream(PidTagDisplayName, PtypString)
        return utf16(_data)

    @staticmethod
    def property_name(tag, typ):
        prop_id = "%04x%04X" % (tag, typ)
        return "%s%s" % (MSG_SUBSTG, prop_id.upper())


class MsgRoot(MsgStorage):

    def __init__(self, cfb, root):
        super().__init__(cfb, root)

    def message_class(self):
        _data = self.stream(PidTagMessageClass, PtypString)
        return utf16(_data)

    def message_id(self):
        _data = self.stream(PidTagInternetMessageId, PtypString)
        return utf16(_data)

    def display_to(self):
        _data = self.stream(PidTagDisplayTo, PtypString)
        return utf16(_data)

    def display_cc(self):
        _data = self.stream(PidTagDisplayCc, PtypString)
        return utf16(_data)

    def display_bcc(self):
        _data = self.stream(PidTagDisplayBcc, PtypString)
        return utf16(_data)

    def sender_name(self):
        _data = self.stream(PidTagSenderName, PtypString)
        return utf16(_data)

    def sender_email_address(self):
        _data = self.stream(PidTagSenderEmailAddress, PtypString)
        return utf16(_data)

    def sender_smtp_address(self):
        _data = self.stream(PidTagSenderSmtpAddress, PtypString)
        return utf16(_data)

    def subject(self):
        _data = self.stream(PidTagSubject, PtypString)
        return utf16(_data)

    def body_content_id(self):
        _data = self.stream(PidTagBodyContentId, PtypString)
        return utf16(_data)

    def body_text(self):
        _data = self.stream(PidTagBody, PtypString)
        return utf16(_data)

    def body_html(self):
        _data = self.stream(PidTagBodyHtml, PtypString)
        if _data is None:
            return self.rtf_as_html()
        else:
            return utf16(_data)

    def body_rtf(self):
        _data = self.stream(PidTagRtfCompressed, PtypBinary)
        return self._decompress(_data)

    def rtf_in_sync(self):
        return self.props.get_property_bool(PidTagRtfInSync, PtypBoolean)[1]

    def has_attachments(self):
        return self.props.get_property_bool(PidTagHasAttachments, PtypBoolean)[1]

    def num_recipients(self):
        return self.props.num_recipients()

    def num_attachments(self):
        return self.props.num_attachments()

    def message_delivery_time(self):
        time = self.props.get_property_int64(PidTagMessageDeliveryTime, PtypTime)
        return filetime2datetime(time[1])

    def message_submit_time(self):
        time = self.props.get_property_int64(PidTagClientSubmitTime, PtypTime)
        return filetime2datetime(time[1])

    def message_receipt_time(self):
        time = self.props.get_property_int64(PidTagReceiptTime, PtypTime)
        return filetime2datetime(time[1])

    def rtf_as_html(self):
        data = self.body_rtf()
        if data is None:
            return None
        else:
            return RtfParser(data.decode("utf-8")).decode_html()

    def rtf_as_text(self):
        data = self.body_rtf()
        if data is None:
            return None
        else:
            return RtfParser(data.decode("utf-8")).decode_text()

    @staticmethod
    def _decompress(data):
        if data is not None and len(data) >= RTF_MIN_SIZE:
            try:
                return decompress(data)
            except Exception as e:
                log.error(str(e))
        return None


class MsgEmbedded(MsgRoot):
    __slots__ = ['attachments', 'recipients']

    def __init__(self, cfb, root):
        super().__init__(cfb, root)
        self.attachments, self.recipients = self.initialize()

    def initialize(self):
        attachments, recipients = [], []
        for child in self.data.children:
            entry = self.cfb.cfb_root.entry(child)
            name = entry.directory_entry_name()
            if name.startswith(MSG_ATTACH):
                attachments.append(entry)
            elif name.startswith(MSG_RECIP):
                recipients.append(entry)

        return MsgAttachments(self.cfb, attachments), MsgRecipients(self.cfb, recipients)

    def get_root(self):
        return self

    def get_recipients(self):
        return self.recipients

    def get_attachments(self):
        return self.attachments


class MsgAttachment(MsgStorage):

    def __init__(self, cfb, attachment):
        super().__init__(cfb, attachment)

    def get_attachment(self):
        return self.stream(PidTagAttachDataBinary, PtypBinary)

    def get_embedded_attachment(self):
        data = self.find(PidTagAttachDataObject, PtypObject)
        if data is None:
            return None
        else:
            return MsgEmbedded(self.cfb, data)

    def is_attachment_object(self):
        _data = self.find(PidTagAttachDataObject, PtypObject)
        return False if _data is None else True

    def get_attachment_file_name(self):
        _data = self.stream(PidTagAttachLongFilename, PtypString)
        return utf16(_data)

    def get_attachment_mime(self):
        _data = self.stream(PidTagAttachMimeTag, PtypString)
        return utf16(_data)

    def get_attachment_size(self):
        _data = self.stream(PidTagAttachSize, PtypInteger32)
        return int32(_data)

    def get_attachment_number(self):
        return self.props.get_property(PidTagAttachNumber, PtypInteger32)[1]

    def get_attachment_content_id(self):
        _data = self.stream(PidTagAttachContentId, PtypString)
        return utf16(_data)

    def get_object_type(self):
        return self.props.get_property(PidTagObjectType, PtypInteger32)[1]

    def get_attach_method(self):
        return self.props.get_property(PidTagAttachMethod, PtypInteger32)[1]

    def is_attachment_msg(self):
        return "message/rfc822" == self.get_attachment_mime()


class MsgAttachments:
    __slots__ = ['attachments']

    def __init__(self, cfb, attachments=None):
        if attachments is None:
            attachments = cfb.cfb_root.select_entry_by_name(MSG_ATTACH)
        self.attachments = [MsgAttachment(cfb, attachment) for attachment in attachments]

    def __len__(self):
        return len(self.attachments)

    def __getitem__(self, item):
        assert 0 <= item < len(self.attachments)
        return self.attachments[item]


class MsgRecipient(MsgStorage):

    def __init__(self, cfb, recipient):
        super().__init__(cfb, recipient)

    def get_recipient_display_name(self):
        _data = self.stream(PidTagRecipientDisplayName, PtypString)
        return utf16(_data)

    def get_smtp_address(self):
        _data = self.stream(PidTagSmtpAddress, PtypString)
        return utf16(_data)

    def get_email_address(self):
        _data = self.stream(PidTagEmailAddress, PtypString)
        return utf16(_data)


class MsgRecipients:
    __slots__ = ['recipients']

    def __init__(self, cfb, recipients=None):
        if recipients is None:
            recipients = cfb.cfb_root.select_entry_by_name(MSG_RECIP)
        self.recipients = [MsgRecipient(cfb, recipient) for recipient in recipients]

    def __len__(self):
        return len(self.recipients)

    def __getitem__(self, item):
        assert 0 <= item < len(self.recipients)
        return self.recipients[item]


class Msg(MsgRoot):
    __slots__ = ['named_props', 'recipients', 'attachments']

    def __init__(self, fp):
        cfb = Cfb(fp)
        super().__init__(cfb, cfb.cfb_root.root())
        self.named_props = MsgNamedProperties(cfb)
        self.recipients = MsgRecipients(cfb)
        self.attachments = MsgAttachments(cfb)

    def get_root(self):
        return self

    def get_recipients(self):
        return self.recipients

    def get_attachments(self):
        return self.attachments
