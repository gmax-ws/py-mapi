import struct

__all_ = ['int8', 'uint8', 'int16', 'uint16', 'int32',
          'uint32', 'int64', 'uint64', 'utf8', 'utf16',
          'uint16be', 'uint32be', 'to_hex', 'guid', 'override']


def override(f):
    return f


def int8(data):
    return None if data is None else struct.unpack("b", data)[0]


def uint8(data):
    return None if data is None else struct.unpack("B", data)[0]


def int16(data):
    return None if data is None else struct.unpack("<h", data)[0]


def uint16(data):
    return None if data is None else struct.unpack("<H", data)[0]


def uint16be(data):
    return None if data is None else struct.unpack(">H", data)[0]


def int32(data):
    return None if data is None else struct.unpack("<i", data)[0]


def uint32(data):
    return None if data is None else struct.unpack("<I", data)[0]


def uint32be(data):
    return None if data is None else struct.unpack(">I", data)[0]


def int64(data):
    return None if data is None else struct.unpack("<q", data)[0]


def uint64(data):
    return None if data is None else struct.unpack("<Q", data)[0]


def float(data):
    return None if data is None else struct.unpack("<f", data)[0]


def double(data):
    return None if data is None else struct.unpack("<d", data)[0]


def utf8(data):
    return None if data is None else data.decode("utf-8")


def utf16(data):
    return None if data is None else data.decode("utf-16")


def to_hex(data):
    return "".join(["%02X" % b for b in data])


def guid(data):
    data1 = to_hex(data[0:4])
    data2 = to_hex(data[4:6])
    data3 = to_hex(data[6:8])
    data4a = to_hex(data[8:10])
    data4b = to_hex(data[10:])
    return "%s-%s-%s-%s-%s" % (data1, data2, data3, data4a, data4b)
