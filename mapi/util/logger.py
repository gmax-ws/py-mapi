import logging

formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

handler = logging.StreamHandler()
handler.setFormatter(formatter)

log = logging.getLogger()
log.addHandler(handler)
log.setLevel(logging.DEBUG)


def set_file_handler(file_handler):
    file_handler = logging.FileHandler(file_handler)
    file_handler.setFormatter(formatter)
    log.addHandler(file_handler)


# set_file_handler("mapi.log")
