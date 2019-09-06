import logging

logging.basicConfig(format = '%(asctime)s %(module)s %(levelname)s %(message)s', level = logging.CRITICAL)

log = logging.getLogger("daqseq")
log.setLevel(100)