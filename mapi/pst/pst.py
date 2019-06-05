from mapi.pst.amap import *
from mapi.pst.nbd import *


class Pst:
    __slots__ = ['fp', 'header', 'root', 'amap']

    def __init__(self, fp):
        self.fp = fp
        self.header = HEADER(fp.read(PST_HEADER_SIZE))
        self.root = self.header.root()
        self.amap = PstAMap(fp, self.root.amap_last())

        for a in self.amap:
            print(a[0], hex(a[1].trailer().ptype()), hex(a[1].trailer().ptype_repeat()))
        print(len(self.amap), self.amap[0])
        # x = self.amap[0]
        # for i in range(0, 496):
        #     print(x.get_block(i))

        print(self.amap.total_blocks())

        nbt = Nbt(self.root.bref_nbt(), self.fp)
        nbt.nbt_traverse()
