
import sys
import os
import os.path
import shutil

if sys.hexversion >= 0x03000000:
    open_file = open
else:
    import codecs
    open_file = codecs.open


BASEDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                       os.path.pardir)


def copyTree(src: str, dst: str, symlinks: bool = False, ignore=None):
    src = os.path.abspath(src)
    dst = os.path.abspath(dst)

    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            if os.path.exists(d):
                shutil.rmtree(d)

            shutil.copytree(s, d, symlinks, ignore)
        else:
            if os.path.exists(d):
                shutil.os.remove(d)

            shutil.copy2(s, d)


def copyFile(s: str, d: str):
    if os.path.exists(d):
        shutil.os.remove(d)
    shutil.copy2(s, d)


def hasWriteAccess(path: str):
    if not os.path.exists(os.path.abspath(path)):
        return os.path.exists(os.path.dirname(path)) and os.access(os.path.abspath(path), os.W_OK)
    else:
        return os.access(os.path.abspath(path), os.W_OK)
