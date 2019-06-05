"""
Compressed Rich Text Format (RTF) worker

Based on Rich Text Format (RTF) Compression Algorithm
https://msdn.microsoft.com/en-us/library/cc463890(v=exchg.80).aspx
"""

import sys
from io import BytesIO

from mapi.util.crc32 import crc32
from mapi.util.decoder import *

__all__ = ['decompress']

PY3 = sys.version_info[0] == 3

INIT_DICT = (
    b'{\\rtf1\\ansi\\mac\\deff0\\deftab720{\\fonttbl;}{\\f0\\fnil \\froman \\'
    b'fswiss \\fmodern \\fscript \\fdecor MS Sans SerifSymbolArialTimes New '
    b'RomanCourier{\\colortbl\\red0\\green0\\blue0\r\n\\par \\pard\\plain\\'
    b'f0\\fs20\\b\\i\\u\\tab\\tx'
)

INIT_DICT_SIZE = 207
MAX_DICT_SIZE = 4096

COMPRESSED = b'LZFu'
UNCOMPRESSED = b'MELA'


def decompress(data):
    """
    Decompress `data` using RTF compression algorithm
    """
    # set init dict
    if len(data) < 16:
        raise Exception('Data must be at least 16 bytes long')
    init_dict = list(INIT_DICT + b' ' * (MAX_DICT_SIZE - INIT_DICT_SIZE))
    write_offset = INIT_DICT_SIZE
    output_buffer = []
    # make stream
    in_stream = BytesIO(data)

    # read compressed RTF header
    comp_size = uint32(in_stream.read(4))
    raw_size = uint32(in_stream.read(4))
    comp_type = in_stream.read(4)
    crc_value = uint32(in_stream.read(4))

    # get only data
    contents = BytesIO(in_stream.read(comp_size - 12))

    if comp_type == COMPRESSED:
        # check CRC
        if crc_value != crc32(contents.read()):
            raise Exception('CRC is invalid! The file is corrupt!')
        contents.seek(0)
        end = False
        while not end:
            val = contents.read(1)
            if val:
                control = '{0:08b}'.format(ord(val))
                # check bits from LSB to MSB
                for i in range(1, 9):
                    if control[-i] == '1':
                        # token is reference (16 bit)
                        token = uint16be(contents.read(2))  # big-endian
                        if token is not None:
                            # extract [12 bit offset][4 bit length]
                            offset = (token >> 4) & 0b111111111111
                            # end indicator
                            end = write_offset == offset
                            if not end:
                                length = token & 0b1111
                                actual_length = length + 2
                                for step in range(actual_length):
                                    read_offset = (offset + step) % MAX_DICT_SIZE
                                    char = init_dict[read_offset]
                                    output_buffer.append(bytes([char]) if PY3 else char)
                                    init_dict[write_offset] = char
                                    write_offset = (write_offset + 1) % MAX_DICT_SIZE
                    else:
                        # token is literal (8 bit)
                        val = contents.read(1)
                        if val:
                            output_buffer.append(val)
                            init_dict[write_offset] = ord(val) if PY3 else val
                            write_offset = (write_offset + 1) % MAX_DICT_SIZE

        return b"".join(output_buffer)
    elif comp_type == UNCOMPRESSED:
        return contents.read(raw_size)
    else:
        raise Exception('Unknown type of RTF compression!')
