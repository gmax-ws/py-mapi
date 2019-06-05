from mapi.pst.nbd import *
from mapi.util.decoder import *

__all__ = ['NID', 'BTPAGE', 'BTENTRY', 'NBTENTRY']

MASK_NID_TYPE_NORMAL_FOLDER = 0x400
MASK_NID_TYPE_SEARCH_FOLDER = 0x4000
MASK_NID_TYPE_NORMAL_MESSAGE = 0x10000
MASK_NID_TYPE_ASSOC_MESSAGE = 0x8000
MASK_NID_TYPE_ANY = 0x400

NID_TYPE_HID = 0x00  # Heap node
NID_TYPE_INTERNAL = 0x01  # Internal node (section 2.4.1)
NID_TYPE_NORMAL_FOLDER = 0x02  # Normal Folder object (PC)
NID_TYPE_SEARCH_FOLDER = 0x03  # Search Folder object (PC)
NID_TYPE_NORMAL_MESSAGE = 0x04  # Normal Message object (PC)
NID_TYPE_ATTACHMENT = 0x05  # Attachment object (PC)
NID_TYPE_SEARCH_UPDATE_QUEUE = 0x06  # Queue of changed objects for search Folder objects
NID_TYPE_SEARCH_CRITERIA_OBJECT = 0x07  # Defines the search criteria for a search Folder object
NID_TYPE_ASSOC_MESSAGE = 0x08  # Folder associated information (FAI) Message object (PC)
NID_TYPE_CONTENTS_TABLE_INDEX = 0x0A  # Internal, persisted view-related
NID_TYPE_RECEIVE_FOLDER_TABLE = 0x0B  # Receive Folder object (Inbox)
NID_TYPE_OUTGOING_QUEUE_TABLE = 0x0C  # Outbound queue (Outbox)
NID_TYPE_HIERARCHY_TABLE = 0x0D  # Hierarchy table (TC)
NID_TYPE_CONTENTS_TABLE = 0x0E  # Contents table (TC)
NID_TYPE_ASSOC_CONTENTS_TABLE = 0x0F  # FAI contents table (TC)
NID_TYPE_SEARCH_CONTENTS_TABLE = 0x10  # Contents table (TC) of a search Folder object
NID_TYPE_ATTACHMENT_TABLE = 0x11  # Attachment table (TC)
NID_TYPE_RECIPIENT_TABLE = 0x12  # Recipient table (TC)
NID_TYPE_SEARCH_TABLE_INDEX = 0x13  # Internal, persisted view-related
NID_TYPE_LTP = 0x1F  # LTP

NBTENTRY_SIZE = 32
BTENTRY_SIZE = 24


class NID:
    """
    Nodes provide the primary abstraction used to reference data stored in the PST file that is not
    interpreted by the NDB layer. Each node is identified using its NID. Each NID is unique within the
    namespace in which it is used. Each node referenced by the NBT MUST have a unique NID. However,
    two subnodes of two different nodes can have identical NIDs, but two subnodes of the same node
    MUST have different NIDs.
    """
    __slots__ = ['data']

    def __init__(self, data):
        self.data = data

    def nid_type(self):
        """
        nidType (5 bits): Identifies the type of the node represented by the NID. The following table
        specifies a list of values for nidType. However, it is worth noting that nidType has no meaning to
        the structures defined in the NDB Layer.
        :return:
        """
        return uint8(self.data[0:1]) & 0x1F

    def nid_index(self):
        """
        nidIndex (27 bits): The identification portion of the NID.
        :return:
        """
        return uint32(self.data[0:4]) >> 5


class NBTENTRY:
    """
    NBTENTRY records contain information about nodes and are found in BTPAGES with cLevel equal to 0,
    with the ptype of ptypeNBT. These are the leaf entries of the NBT.
    """
    __slots__ = ['data']

    def __init__(self, data):
        self.data = data
        assert (len(data) == 32)

    def nid(self):
        """
        The NID (section 2.2.2.1) of the entry. Note that the NID is a 4-byte value for both
        Unicode and ANSI formats. However, to stay consistent with the size of the btkey member
        in BTENTRY, the 4-byte NID is extended to its 8-byte equivalent for Unicode PST files.
        :return:
        """
        return NID(self.data[0:8])

    def bid_data(self):
        """
        The BID of the data block for this node.
        :return:
        """
        return BID(self.data[8:16])

    def bid_sub(self):
        """
        The BID of the subnode block for this node. If this value is zero,
        a subnode block does not exist for this node.
        :return:
        """
        return BID(self.data[16:24])

    def nid_parent(self):
        """
        If this node represents a child of a Folder object defined in the Messaging
        Layer, then this value is nonzero and contains the NID of the parent Folder object's node.
        Otherwise, this value is zero. See section 2.2.2.7.7.4.1 for more information. This field is not
        interpreted by any structure defined at the NDB Layer.
        :return:
        """
        return NID(self.data[24:28])


class BBTENTRY:
    """
    BBTENTRY records contain information about blocks and are found in BTPAGES with cLevel equal to
    0, with the ptype of "ptypeBBT". These are the leaf entries of the BBT. As noted in section
    2.2.2.7.7.1, these structures MAY NOT be tightly packed and the cbEnt field of the BTPAGE SHOULD
    be used to iterate over the entries.
    """
    __slots__ = ['data']

    def __init__(self, data):
        self.data = data
        assert (len(data) == 24)

    def bref(self):
        """
        BREF structure (section 2.2.2.4) that contains the BID and IB of the block that the BBTENTRY references.
        :return:
        """
        return BREF(self.data[0:16])

    def cb(self):
        """
        The count of bytes of the raw data contained in the block referenced by BREF
        excluding the block trailer and alignment padding, if any.
        :return:
        """
        return uint16(self.data[16:18])

    def ref(self):
        """
        Reference count indicating the count of references to this block.
        See section 2.2.2.7.7.3.1 regarding how reference counts work.
        :return:
        """
        return uint16(self.data[18:20])


class BTENTRY:
    """
    BTENTRY records contain a key value (NID or BID) and a reference
    to a child BTPAGE page in the BTree.
    """
    __slots__ = ['data']

    def __init__(self, data):
        self.data = data
        assert (len(self.data) == 24)

    def btkey(self, ptype):
        """
        The key value associated with this BTENTRY. All the entries in the child BTPAGE
        referenced by BREF have key values greater than or equal to this key value.
        The btkey is either an NID (zero extended to 8 bytes for Unicode PSTs) or a BID,
        depending on the ptype of the page.
        :return:
        """
        if ptype == 0x80:
            return BID(self.data[0:8])
        elif ptype == 0x81:
            return NID(self.data[0:8])
        else:
            raise Exception("Invalid ptype %04x", ptype)

    def bref(self):
        """
        BREF structure that points to the child BTPAGE.
        :return:
        """
        return BREF(self.data[8:24])


class BTPAGE:
    """
    A BTPAGE structure implements a generic BTree using 512-byte pages.
    """
    __slots__ = ['data']

    def __init__(self, data):
        self.data = data
        assert (len(data) == 512)

    def rgentries(self):
        """
        Entries of the BTree array. The entries in the array depend on the value of the cLevel field.
        If cLevel is greater than 0, then each entry in the array is of type BTENTRY.
        If cLevel is 0, then each entry is either of type BBTENTRY or NBTENTRY, depending on the ptype
        of the page.
        :return:
        """
        return self.data[0:488]

    def ent(self):
        """
        The number of BTree entries stored in the page data.
        :return:
        """
        return uint8(self.data[488:489])

    def ent_max(self):
        """
        The maximum number of entries that can fit inside the page data.
        :return:
        """
        return uint8(self.data[489:490])

    def cb_ent(self):
        """
        The size of each BTree entry, in bytes. Note that in some cases, cbEnt can be
        greater than the corresponding size of the corresponding rgentries structure because of
        alignment or other considerations. Implementations MUST use the size specified in cbEnt to
        advance to the next entry.
        :return:
        """
        return uint8(self.data[490:491])

    def level(self):
        """
        The depth level of this page. Leaf pages have a level of zero, whereas intermediate pages
        have a level greater than 0. This value determines the type of the entries in rgentries, and
        is interpreted as unsigned.
        :return:
        """
        return uint8(self.data[491:492])

    def page_trailer(self):
        """
        A PAGETRAILER structure.The ptype subfield of pageTrailer MUST be set to ptypeBBT for a
        Block BTree page, or ptypeNBT for a Node BTree page. The other subfields of pageTrailer
        MUST be set as specified in section 2.2.2.7.1.
        :return:
        """
        from mapi.pst.amap import PAGETRAILER
        return PAGETRAILER(self.data[496:512])
