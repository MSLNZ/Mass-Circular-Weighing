import logging

logging.basicConfig(format = '%(asctime)s %(module)s %(levelname)s %(message)s', level = logging.INFO)

log = logging.getLogger("daqseq")
# log.setLevel(100)