import io
from math import pow

from mapi.util.decoder import *
from mapi.util.logger import log

__all__ = ['Cfb', 'MSG_ROOT', 'MSG_NAMEID', 'MSG_RECIP', 'MSG_ATTACH', 'MSG_SUBSTG', 'MSG_EMBEDDED', 'MSG_PROPS']

DEBUG = False

HEADER_SIZE = 512
HEADER_SIGNATURE = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"
HEADER_CLSID_NULL = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
HEADER_BYTE_ORDER = 0xFFFE

FAT_ENTRY_SIZE = 4
DIR_ENTRY_SIZE = 128

VERSION_3 = 3
SECTOR_SIZE_3 = 512
VERSION_4 = 4
SECTOR_SIZE_4 = 4096
MINI_SECTOR_SIZE = 64

OBJ_TYPE_UNALLOCATED = 0
OBJ_TYPE_STORAGE = 1
OBJ_TYPE_STREAM = 2
OBJ_TYPE_ROOT_STORAGE = 5

types = {OBJ_TYPE_UNALLOCATED: "unallocated",
         OBJ_TYPE_STORAGE: "storage",
         OBJ_TYPE_STREAM: "stream",
         OBJ_TYPE_ROOT_STORAGE: "root"}

COLOR_RED = 0
COLOR_BLACK = 1

FREESECT = 0xFFFFFFFF
ENDOFCHAIN = 0xFFFFFFFE
DIFSECT = 0xFFFFFFFC
FATSECT = 0xFFFFFFFD
MAXREGSECT = 0xFFFFFFFA

MSG_ROOT = "Root Entry"
MSG_NAMEID = "__nameid_version1.0"
MSG_RECIP = "__recip_version1.0"
MSG_ATTACH = "__attach_version1.0"
MSG_SUBSTG = "__substg1.0_"
MSG_PROPS = "__properties_version1.0"
MSG_EMBEDDED = "__substg1.0_3701000D"


class CfbHeader:
    __slots__ = ['header']

    def __init__(self, _data):
        self.header = _data
        self._validation()

    def _validation(self):
        assert (len(self.header) == HEADER_SIZE)

        hdr_signature = self.header[0:8]
        assert (hdr_signature == HEADER_SIGNATURE)

        assert (self.header[8:24] == HEADER_CLSID_NULL)

        byte_order = uint16(self.header[28:30])
        assert (byte_order == HEADER_BYTE_ORDER)

        minor, major = self.version()
        assert (major in (VERSION_3, VERSION_4))

        sector_size = self.sector_size()

        if major == VERSION_3:
            assert (sector_size == SECTOR_SIZE_3)

        if major == VERSION_4:
            assert (sector_size == SECTOR_SIZE_4)

        log.debug("version: %d.%d sector size: %d FAT size: %d" %
                  (major, minor, sector_size, self.fat_size()))
        log.debug("mini FAT location: %d mini FAT size: %d" %
                  (self.mini_fat_sector(), self.mini_fat_size()))
        log.debug("mini stream sector size: %d mini stream size cutoff: %d" %
                  (self.mini_stream_sector_size(), self.mini_stream_size_cutoff()))

    def version(self):
        return uint16(self.header[24:26]), uint16(self.header[26:28])

    def sector_size(self):
        size = uint16(self.header[30:32])
        return int(pow(2, size))

    def directory_sector(self):
        return uint32(self.header[48:52])

    def fat_size(self):
        return uint32(self.header[44:48])

    def difat_size(self):
        return uint32(self.header[72:76])

    def first_difat(self):
        return uint32(self.header[68:72])

    def mini_fat_sector(self):
        return uint32(self.header[60:64])

    def mini_fat_size(self):
        return uint32(self.header[64:68])

    def mini_stream_sector_size(self):
        size = uint32(self.header[32:36])
        return int(pow(2, size))

    def mini_stream_size_cutoff(self):
        return uint32(self.header[56:60])


class CfbDiFat:
    __slots__ = ['difat']

    def __init__(self, _data):
        self.difat = _data
        log.debug("difat: %s" % self.difat)


class CfbFatBase:
    __slots__ = ['fat', 'sector_size', 'type']

    def __init__(self, _data, sector_size, _type=None):
        self.fat = _data
        self.sector_size = sector_size
        self.type = _type
        log.debug("fat (%d): %s" % (self.sector_size, self.fat))

    def offset(self, sector_number):
        pass


class CfbFat(CfbFatBase):

    def offset(self, sector_number):
        return (sector_number + 1) * self.sector_size, self.sector_size


class CfbMiniFat(CfbFatBase):

    def offset(self, sector_number):
        return int(sector_number * self.sector_size)


class CfbDirectory:
    __slots__ = ['entries']

    def __init__(self, _data):
        self.entries = _data
        assert (_data[0].object_type() == OBJ_TYPE_ROOT_STORAGE)
        log.debug("directory entries: %d" % len(_data))
        for i in range(0, len(self.entries)):
            self.entries[i].index = i
            if DEBUG:
                self.entries[i].info()
        self._make_tree()

    def _make_tree(self):
        log.debug("make tree")
        for entry in self.entries:
            if entry.object_type() in (OBJ_TYPE_STORAGE, OBJ_TYPE_ROOT_STORAGE):
                entry.set_children(self.add_children(entry))

    def add_children(self, entry):
        children = []
        if 0 <= entry.child_id() <= MAXREGSECT:
            children.append(entry.child_id())
            child = self.entries[entry.child_id()]
            self.traverse(child, children)
        return sorted(children)

    def traverse(self, child, children):
        if child.left_sibling() != FREESECT:
            children.append(child.left_sibling())
            self.traverse(self.entries[child.left_sibling()], children)

        if child.right_sibling() != FREESECT:
            children.append(child.right_sibling())
            self.traverse(self.entries[child.right_sibling()], children)

    def find_entry_by_name(self, name):
        root = self.entries[0]
        assert (root.object_type() == OBJ_TYPE_ROOT_STORAGE)
        for child in root.children:
            if self.entries[child].directory_entry_name() == name:
                return self.entries[child]
        return None

    def select_entry_by_name(self, name):
        group = []
        root = self.entries[0]
        assert (root.object_type() == OBJ_TYPE_ROOT_STORAGE)
        for child in root.children:
            if self.entries[child].directory_entry_name().startswith(name):
                group.append(self.entries[child])
        return group

    def root(self):
        return self.entries[0]

    def entry(self, index):
        assert (0 <= index < len(self.entries))
        return self.entries[index]

    def recipients(self):
        return self.select_entry_by_name(MSG_RECIP)

    def attachments(self):
        return self.select_entry_by_name(MSG_ATTACH)

    def named_properties(self):
        return self.select_entry_by_name(MSG_NAMEID)

    def properties(self):
        return self.select_entry_by_name(MSG_PROPS)

    def debug(self, name):
        entry = self.find_entry_by_name(name)
        entry.info()
        for child in entry.children:
            self.entries[child].info()

    def all(self):
        for entry in self.entries:
            entry.info()


class CfbStorage:
    __slots__ = ['index', 'data', 'children']

    def __init__(self, _data):
        self.data = _data
        self.children = None
        self.index = 0

    def info(self):
        log.debug("/---")
        log.debug("index: %d name: %s type: %d (%s)" %
                  (self.index, self.directory_entry_name(),
                   self.object_type(), types[self.object_type()]))
        log.debug("starting_sector: %d" % self.starting_sector())
        log.debug("siblings: %d %d" % (self.left_sibling(), self.right_sibling()))
        log.debug("child id: %d" % self.child_id())
        log.debug("stream size: %d" % self.stream_size())

    def set_children(self, children):
        self.children = children

    def directory_entry_name(self):
        length = self.directory_entry_name_length()
        return utf16(self.data[0:length - 2])

    def directory_entry_name_length(self):
        return uint16(self.data[64:66])

    def object_type(self):
        return uint8(self.data[66:67])

    def color_flag(self):
        color = uint8(self.data[67:68])
        assert (color in (COLOR_RED, COLOR_BLACK))
        return color

    def left_sibling(self):
        return uint32(self.data[68:72])

    def right_sibling(self):
        return uint32(self.data[72:76])

    def child_id(self):
        return uint32(self.data[76:80])

    def starting_sector(self):
        return uint32(self.data[116:120])

    def stream_size(self):
        return uint64(self.data[120:128])


class CfbMiniStream:
    __slots__ = ['stream']

    def __init__(self, data):
        self.stream = data

    def read_sector(self, sector):
        return self.stream[sector]


class Cfb:
    __slots__ = ['fp', 'sector_size', 'mini_sector_size', 'cfb_header', 'cfb_root',
                 'cfb_difat', 'cfb_fat', 'cfb_mini_fat', 'cfb_mini_stream']

    def __init__(self, fp):
        self.fp = fp
        self.sector_size = SECTOR_SIZE_3
        self.mini_sector_size = MINI_SECTOR_SIZE
        self.cfb_header = None
        self.cfb_root = None
        self.cfb_difat = None
        self.cfb_fat = None
        self.cfb_mini_fat = None
        self.cfb_mini_stream = None
        self._init()

    def _init(self):
        self._header()
        self._difat()
        self._fat()
        self._mini_fat()
        self._root_entry()
        self._mini_stream()

    def select_fat(self, stream_size):
        size_cutoff = self.cfb_header.mini_stream_size_cutoff()
        return self.cfb_mini_fat if stream_size < size_cutoff else self.cfb_fat

    def _header(self):
        self.fp.seek(0, io.SEEK_SET)
        header = self.fp.read(HEADER_SIZE)
        self.cfb_header = CfbHeader(header)
        self.sector_size = self.cfb_header.sector_size()
        self.mini_sector_size = self.cfb_header.mini_stream_sector_size()

    def _root_entry(self):
        _data = []

        fat_obj = self.cfb_fat
        _start = self.cfb_header.directory_sector()

        while _start != ENDOFCHAIN:
            _data.append(self._read_sector(fat_obj, _start))
            _next = fat_obj.fat[_start]
            _start = _next

        _data = b"".join(_data)
        buffer = [CfbStorage(_data[i:i + DIR_ENTRY_SIZE])
                  for i in range(0, len(_data), DIR_ENTRY_SIZE)
                  if _data[i:i + DIR_ENTRY_SIZE][66] != OBJ_TYPE_UNALLOCATED]

        self.cfb_root = CfbDirectory(buffer)

    def _difat(self):
        difat = self.split(self.cfb_header.header[76:512])

        _next_difat = self.cfb_header.first_difat()
        while _next_difat != ENDOFCHAIN:
            _data = self._read_file_sector(_next_difat)
            difat.extend(self.split(_data[0:508]))
            _next_difat = uint32(_data[508:512])

        self.cfb_difat = CfbDiFat(difat)

    def _fat(self):
        fat = []
        for entry in self.cfb_difat.difat:
            if 0 <= entry <= MAXREGSECT:
                fat.extend(self.split(self._read_file_sector(entry)))
        self.cfb_fat = CfbFat(fat, self.sector_size)

    def _mini_fat(self):
        mini_fat = []

        _start = self.cfb_header.mini_fat_sector()

        while _start != ENDOFCHAIN:
            mini_fat.extend(self.split(self._read_file_sector(_start)))
            _next = self.cfb_fat.fat[_start]
            _start = _next

        self.cfb_mini_fat = CfbMiniFat(mini_fat, self.mini_sector_size, 0)

    def _read_storage(self, storage):
        assert (storage.object_type() == OBJ_TYPE_STORAGE)
        _start = storage.child_id()
        assert (_start < len(self.cfb_root.entries))
        return self.cfb_root.entries[_start]

    def _read_stream(self, stream):
        if stream is None:
            return None

        assert (stream.object_type() == OBJ_TYPE_STREAM)

        stream_size = stream.stream_size()
        if stream_size == 0:
            return None

        buffer = []
        fat_obj = self.select_fat(stream_size)
        _start = stream.starting_sector()

        while _start != ENDOFCHAIN:
            if fat_obj.type is None:
                buffer.append(self._read_sector(fat_obj, _start))
            else:
                buffer.append(self.cfb_mini_stream.read_sector(_start))
            _next = fat_obj.fat[_start]
            _start = _next

        return b"".join(buffer)[0:stream_size]

    def _mini_stream(self):
        root = self.cfb_root.root()
        assert (root.object_type() == OBJ_TYPE_ROOT_STORAGE)

        stream_size = root.stream_size()
        if stream_size == 0:
            return None

        buffer = []
        _start = root.starting_sector()

        while _start != ENDOFCHAIN:
            buffer.append(self._read_file_sector(_start))
            _next = self.cfb_fat.fat[_start]
            _start = _next

        _data = b"".join(buffer)[0:stream_size]
        self.cfb_mini_stream = CfbMiniStream([_data[i:i + self.mini_sector_size]
                                              for i in range(0, len(_data), self.mini_sector_size)])

    def _read_sector(self, fat_obj, sector_number):
        offset, sector_size = fat_obj.offset(sector_number)
        self.fp.seek(offset, io.SEEK_SET)
        return self.fp.read(sector_size)

    def _read_file_sector(self, sector_number):
        offset = self.offset(sector_number, self.sector_size)
        self.fp.seek(offset, io.SEEK_SET)
        return self.fp.read(self.sector_size)

    def find_stream(self, root, property_name):
        for child in root.children:
            entry = self.cfb_root.entry(child)
            if entry.directory_entry_name() == property_name:
                return entry
        return None

    def read_stream(self, root, property_name):
        stm = self.find_stream(root, property_name)
        return None if stm is None else self._read_stream(stm)

    def dump(self, root):
        print(root.directory_entry_name())
        for child in root.children:
            entry = self.cfb_root.entry(child)
            if entry.object_type == OBJ_TYPE_STREAM:
                print(entry.directory_entry_name(), entry.stream_size(), self._read_stream(entry))

    @staticmethod
    def offset(i, size):
        return int((i + 1) * size)

    @staticmethod
    def split(fat_data):
        return [uint32(fat_data[i:i + FAT_ENTRY_SIZE])
                for i in range(0, len(fat_data), FAT_ENTRY_SIZE)]
