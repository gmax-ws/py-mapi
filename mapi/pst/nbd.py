from mapi.pst.crypto import *
from mapi.pst.node import *
from mapi.util.crc32 import *
from mapi.util.decoder import *
from mapi.util.logger import *

__all__ = ['Nbt', 'BID', 'IB', 'BREF', 'HEADER', 'ROOT', 'PST_HEADER_SIZE']

PST_HEADER_SIZE = 512 + 64
PST_ROOT_SIZE = 72
PST_HEADER_SIGNATURE = b"\x21\x42\x44\x4E"
PST_MAGIC_CLIENT = b"\x53\x4D"
CRC_PARTIAL_LENGTH = 471

NDB_CRYPT_NONE = 0x00  # Data blocks are not encoded.
NDB_CRYPT_PERMUTE = 0x01  # Encoded with the Permutation algorithm (section 5.1).
NDB_CRYPT_CYCLIC = 0x02  # Encoded with the Cyclic algorithm (section 5.2).
NDB_CRYPT_EDPCRYPTED = 0x10  # Encrypted with Windows Information Protection.

INVALID_AMAP = 0x00  # One or more AMaps in the PST are INVALID
VALID_AMAP1 = 0x01  # Deprecated. Implementations SHOULD NOT use this value. The AMaps are VALID.<6>
VALID_AMAP2 = 0x02  # The AMaps are VALID.

PAGE_SIZE = 512
BTENTRY_SIZE = 24
NBTENTRY_SIZE = 32
BBTENTRY_SIZE = 24

"""
NDB Layer
"""


class Nbt:
    __slots__ = ['root', 'fp', 'data', 'btp', 'table']

    def __init__(self, root, fp):
        self.fp = fp
        offset = root.ib().ib()
        self.fp.seek(offset)
        self.data = self.fp.read(PAGE_SIZE)
        self.btp = BTPAGE(self.data)
        self.table = self.entries()

    def nbt_traverse(self):
        ptype = self.btp.page_trailer().ptype()
        for e in self.table:
            print(e.btkey(ptype).nid_index())

        print(self.btp.cb_ent(), self.btp.ent(), self.btp.ent_max(), self.btp.level())
        print(self.btp.page_trailer())

    def entries(self):
        n = self.btp.cb_ent()
        entries_size = len(self.btp.rgentries())
        rang = range(0, entries_size, n)
        if self.btp.level() == 0:
            table = [NBTENTRY(self.data[i:i + n]) for i in rang]
        else:
            table = [BTENTRY(self.data[i:i + n]) for i in rang]
        return table[0:self.btp.ent()]


class HEADER:
    """
    The HEADER structure is located at the beginning of the PST file (absolute file offset 0), and contains
    metadata about the PST file, as well as the ROOT information to access the NDB Layer data structures.
    """
    __slots__ = ['header', 'file_version', 'client_version', 'encrypted']

    def __init__(self, _data):
        assert (len(_data) == PST_HEADER_SIZE)
        self.header = _data
        self.file_version = uint16(self.header[10:12])
        self.client_version = uint16(self.header[12:14])
        self.encrypted = self.crypt_method()
        self._validation()
        log.debug("File version: %d" % self.file_version)
        log.debug("Client version: %d" % self.client_version)
        log.debug("Crypt method: %d" % self.encrypted)
        log.debug("Next BID: %d" % self.next_bid().bid_index())
        log.debug("rgnid: %s" % self.rgnid())

    def _validation(self):
        hdr_signature = self.header[0:4]
        assert (hdr_signature == PST_HEADER_SIGNATURE)
        crc_partial = uint32(self.header[4:8])
        crc = crc32(self.header[8:8 + CRC_PARTIAL_LENGTH])
        assert (crc_partial == crc)
        assert (self.header[8:10] == PST_MAGIC_CLIENT)
        assert (self.header[14:24] == b'\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00')
        assert (self.sentinel() == 0x80)
        crc_full = uint32(self.header[524:528])
        crc = crc32(self.header[8:524])
        assert (crc_full == crc)

    def is_ansi(self):
        return self.file_version in (14, 15)

    def is_unicode(self):
        return self.file_version >= 23

    def is_wp(self):
        return self.file_version == 37

    def sentinel(self):
        """
        MUST be set to 0x80.
        :return:
        """
        return uint8(self.header[512:513])

    def crypt_method(self):
        """
        Indicates how the data within the PST file is encoded. MUST be set to one
        of the pre-defined values described in the following table.
        :return:
        """
        return uint8(self.header[513:514])

    def next_bid(self):
        """
        Next BID. This value is the monotonic counter that indicates the BID to be assigned
        for the next allocated block. BID values advance in increments of 4.
        :return:
        """
        return BID(self.header[516:524])

    def root(self):
        """
        A ROOT structure (section 2.2.2.5).
        :return:
        """
        return ROOT(self.header[180:180 + PST_ROOT_SIZE])

    def rgnid(self):
        data = self.header[44:44 + 128]
        return [NID(data[i:i + 4]) for i in range(0, len(data), 4)]

    def decrypt(self, data, key=None):
        encrypt = self.header.encrypted
        if encrypt == NDB_CRYPT_NONE:
            return data
        elif encrypt == NDB_CRYPT_PERMUTE:
            permute(data)
        elif encrypt == NDB_CRYPT_CYCLIC:
            cyclic(data, key)
        elif encrypt == NDB_CRYPT_EDPCRYPTED:
            raise Exception("Windows Information Protection encryption is not supported")
        else:
            raise Exception("Unknown encryption code %d" % encrypt)


class ROOT:
    """
    The ROOT structure contains current file state.
    """
    __slots__ = ['data']

    def __init__(self, data):
        assert (len(data) == PST_ROOT_SIZE)
        self.data = data
        log.debug("PST size: %d" % self.pst_size())

    def pst_size(self):
        """
        The size of the PST file, in bytes.
        :return: size of PST
        """
        return uint64(self.data[4:12])

    def amap_last(self):
        """
        An IB structure that contains the absolute file
        offset to the last AMap page of the PST file.
        :return: IB
        """
        return IB(self.data[12:20])

    def amap_free(self):
        """
        The total free space in all AMaps, combined.
        :return:
        """
        return uint64(self.data[20:28])

    def pmap_free(self):
        """
        The total free space in all PMaps, combined.
        Because the PMap is deprecated, this value SHOULD be zero.
        Creators of new PST files MUST initialize this value to zero.
        :return:
        """
        return uint64(self.data[28:36])

    def bref_nbt(self):
        """
        A BREF structure that references the root page of the Node BTree (NBT).
        :return:
        """
        return BREF(self.data[36:52])

    def bref_bbt(self):
        """
        A BREF structure that references the root page of the Block BTree (BBT).
        :return:
        """
        return BREF(self.data[52:68])

    def amap_valid(self):
        """
        Indicates whether all of the AMaps in this PST file are valid.
        This value MUST be set to one of the pre-defined values specified in the following table.
        :return:
        """
        return uint8(self.data[68:69])


class IB:
    """
    The IB (Byte Index) is used to represent an absolute offset within the PST file with respect to the
    beginning of the file. The IB is a simple unsigned integer value and is 64 bits in Unicode versions
     and 32 bits in ANSI versions.
    """
    __slots__ = ['byte_index']

    def __init__(self, data):
        self.byte_index = uint64(data)

    def ib(self):
        return self.byte_index


class BREF:
    """
    The BREF is a record that maps a BID to its absolute file offset location.
    """
    __slots__ = ['data']

    def __init__(self, data):
        self.data = data

    def bid(self):
        """
        A BID structure, as specified in section 2.2.2.2.
        :return:
        """
        return BID(self.data[0:8])

    def ib(self):
        """
        An IB structure, as specified in section 2.2.2.3.
        :return:
        """
        return IB(self.data[8:16])


class BID:
    """
    Every block allocated in the PST file is identified using the BID structure.
    This structure varies in size according the format of the file. In the case of ANSI files,
    the structure is a 32-bit unsigned value, while in Unicode files it is a 64-bit unsigned long.
    In addition, there are two types of BIDs:

    1. BIDs used in the context of Pages use all of the bits of the structure (below) and are incremented by 1.

    2. Block BIDs reserve the two least significant bits for flags (see below).
        As a result these increment by 4 each time a new one is assigned.
    """
    __slots__ = ['index']

    def __init__(self, data):
        self.index = uint64(data[0:8])

    def r(self):
        """
        Reserved bit. Readers MUST ignore this bit and treat it as zero before
        looking up the BID from the BBT. Writers MUST<4> set this bit to zero.
        :return:
        """
        return self.index & 0x01

    def i(self):
        """
        MUST set to 1 when the block is "Internal", or zero when the block is not "Internal".
        An internal block is an intermediate block that, instead of containing actual data,
        contains metadata about how to locate other data blocks that contain the desired information.
        For more details about technical details regarding blocks, see section 2.2.2.8.
        :return:
        """
        return (self.index >> 1) & 0x01

    def bid_index(self):
        """
        bid index 64 bits including r and i bits
        :return:
        """
        return self.index

    def bid_index62(self):
        """
        bidIndex (Unicode: 62 bits; ANSI: 30 bits): A monotonically increasing value that uniquely
        identifies the BID within the PST file. bidIndex values are assigned based on the bidNextB value in
        the HEADER structure (see section 2.2.2.6). The bidIndex increments by one each time a new BID
        is assigned.
        :return:
        """
        return (self.index >> 2) & 0x3FFFFFFFFFFFFFFF


class BLOCKTRAILER:
    __slots__ = ['data']

    def __init__(self, data):
        assert (len(data) == 16)
        self.data = data

    def cb(self):
        """
        The amount of data, in bytes, contained within the data section of the block. This value
        does not include the block trailer or any unused bytes that can exist after the end of the
        data and before the start of the block trailer.
        :return:
        """
        return uint16(self.data[0:2])

    def sig(self):
        """
        Block signature. See section 5.5 for the algorithm to calculate the block signature.
        :return:
        """
        return uint16(self.data[2:4])

    def crc(self):
        """
        32-bit CRC of the cb bytes of raw data, see section 5.3 for the algorithm to calculate the CRC.
        Note the locations of the dwCRC and bid are differs between the Unicode and ANSI version of this
        structure.
        :return:
        """
        return uint32(self.data[4:8])

    def bid(self):
        """
        The BID (section 2.2.2.2) of the data block.
        :return:
        """
        return BID(self.data[8:16])

    @staticmethod
    def compute_sig(ib, bid):
        """
        calculate block signature
        """
        s = ib ^ bid.index
        return word(word(s >> 16) ^ word(s))
