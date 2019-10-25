
import sys
import os
import os.path

if sys.hexversion >= 0x03000000:
    open_file = open
else:
    import codecs
    open_file = codecs.open


BASEDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                       os.path.pardir)
