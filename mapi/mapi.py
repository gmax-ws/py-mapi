import os
from io import BytesIO

from mapi.cfb.cfb import Cfb
from mapi.msg.msg import Msg
from mapi.pst.pst import Pst

MAX_MEMORY_MSG_FILE_LENGTH = 50000000


class MApi:
    __slots__ = ['file_path', 'ext', 'fp', 'stream']

    def __init__(self, file_path):
        self.file_path = file_path
        self.ext = self.file_path.split('.')[-1].lower()
        self.stream = None

    def __enter__(self):
        file_size = os.path.getsize(self.file_path)
        self.fp = open(self.file_path, mode='rb')
        if file_size < MAX_MEMORY_MSG_FILE_LENGTH:
            content = self.fp.read()
            self.fp.close()
            assert (file_size == len(content))
            stream = BytesIO(content)
        else:
            stream = self.fp

        return self.select(stream)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.stream is not None:
            self.stream.close()

    def select(self, stream):
        if self.ext == 'msg':
            return self.ns_msg(stream)
        elif self.ext == 'pst':
            return self.ns_pst(stream)
        else:
            raise Exception('Unknown file extension %s' % self.ext)

    @staticmethod
    def ns_msg(fp):
        cfb = Cfb(fp)
        return Msg(cfb)

    @staticmethod
    def ns_pst(fp):
        return Pst(fp)
