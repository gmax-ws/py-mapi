from mapi.cfb.cfb import Cfb


class Wrx(Cfb):

    def __init__(self, fp):
        super().__init__(fp)
        for entry in self.cfb_root.entries:
            if entry.object_type() == 2:
                file_name = entry.directory_entry_name()
                with open(file_name, "wb") as fp:
                    fp.write(self._read_stream(entry))
