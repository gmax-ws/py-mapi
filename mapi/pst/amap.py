import io

from mapi.pst.nbd import *
from mapi.util.crc32 import *
from mapi.util.decoder import *

__all__ = ['PstAMap', 'PAGETRAILER']

"""
An AMap page contains an array of 496 bytes that is used to track the space allocation within the data
section that immediately follows the AMap page. Each bit in the array maps to a block of 64 bytes in
the data section. Specifically, the first bit maps to the first 64 bytes of the data section, the second bit
maps to the next 64 bytes of data, and so on. AMap pages map a data section that consists of
253,952 bytes (496 * 8 * 64).
An AMap is allocated out of the data section and, therefore, it actually "maps itself". What this means
is that the AMap actually occupies the first page of the data section and the first byte (that is, 8 bits)
of the AMap is 0xFF, which indicates that the first 512 bytes are allocated for the AMap.
The first AMap of a PST file is located at absolute file offset 0x4400, and subsequent AMaps appear at
intervals of 253,952 bytes thereafter. The following is the structural representation of an AMap page.
"""

AMAP_OFFSET = 0x4400
AMAP_INTERVAL = 253952  # 496*8*64
AMAP_PAGE_SIZE = 512
AMAP_BLOCKS = 496
AMAP_BLOCK_SIZE = 64

ptypeBBT = 0x80  # Block BTree page. Block or page signature.
ptypeNBT = 0x81  # Node BTree page. Block or page signature.
ptypeFMap = 0x82  # Free Map page. 0x0000
ptypePMap = 0x83  # Allocation Page Map page. 0x0000
ptypeAMap = 0x84  # Allocation Map page. 0x0000
ptypeFPMap = 0x85  # Free Page Map page. 0x0000
ptypeDL = 0x86  # Density List page. Block or page signature.


class AMAPPAGE:
    __slots__ = ['amap', 'data']

    def __init__(self, data):
        assert (len(data) == AMAP_INTERVAL)
        self.amap = data[0:AMAP_PAGE_SIZE]
        self.data = data[AMAP_PAGE_SIZE:]
        self.check()

    def map_bits(self):
        return self.amap[0:AMAP_BLOCKS]

    def trailer(self):
        return PAGETRAILER(self.amap[AMAP_BLOCKS:512])

    def check(self):
        crc = self.trailer().crc()
        assert (crc == crc32(self.map_bits()))

    def is_block_allocated(self, block_no):
        assert (0 <= block_no < AMAP_BLOCKS)
        _map = self.map_bits()
        index = block_no >> 3
        mask = 1 << (block_no % 8)
        return bool(uint8(_map[index:index + 1]) & mask)

    def get_block(self, block_no):
        assert (0 <= block_no < AMAP_BLOCKS)
        if self.is_block_allocated(block_no):
            return self.data[block_no:block_no + AMAP_BLOCK_SIZE]
        return None


class PAGETRAILER:
    __slots__ = ['data']

    def __init__(self, data):
        assert (len(data) == 16)
        self.data = data

    def ptype(self):
        return uint8(self.data[0:1])

    def ptype_repeat(self):
        return uint8(self.data[1:2])

    def sig(self):
        return uint16(self.data[2:4])

    def crc(self):
        return uint32(self.data[4:8])

    def bid(self):
        return BID(self.data[8:16])


class PstAMap:
    __slots__ = ['fp', 'page_no', 'eop', 'beg', 'end']

    def __init__(self, fp, eop):
        self.fp = fp
        self.eop = eop
        self.page_no = None
        self.beg = AMAP_OFFSET
        self.end = eop

    def __iter__(self):
        self.page_no = 0
        self.fp.seek(self.beg, io.SEEK_SET)
        return self

    def __next__(self):
        if self.fp.tell() <= self.end.ib():
            self.page_no += 1
            data = self.fp.read(AMAP_INTERVAL)
            amappage = AMAPPAGE(data)
            return self.page_no, amappage
        else:
            raise StopIteration

    def __len__(self):
        return int((self.end.ib() - self.beg) / AMAP_INTERVAL) + 1

    def __getitem__(self, item):
        assert (0 <= item < len(self))
        offset = self.beg + item * AMAP_INTERVAL
        self.fp.seek(offset, io.SEEK_SET)
        data = self.fp.read(AMAP_INTERVAL)
        return AMAPPAGE(data)

    def total_blocks(self):
        return self.__len__() * AMAP_BLOCKS

    def is_block_allocated(self, block_no):
        page, block = self.resolve(block_no)
        amap = self.__getitem__(page)
        return amap.is_block_allocated(block)

    def get_block(self, block_no):
        page, block = self.resolve(block_no)
        amap = self.__getitem__(page)
        return amap.get_block(block)

    @staticmethod
    def resolve(block_no):
        return block_no / AMAP_BLOCKS, block_no % AMAP_BLOCKS
