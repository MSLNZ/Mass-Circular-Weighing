"""Convert a floating point number to an easily readable string"""

from ..log import log


def greg_format(number):
    """Convert a floating point number into a string in Greg's format: 0.000 000 000.
    If this isn't possible, the number is returned as a string with no extra spaces."""
    try:
        before, after = '{:.9f}'.format(number).split('.')
        return before + '.' + ' '.join(after[i:i+3] for i in range(0, len(after), 3)) + '  '
    except ValueError as e:
        log.error("Couldn't put {} in Greg format. {}".format(number, e))
        return str(number)
