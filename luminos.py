#!/usr/bin/env python3

"""Simple launcher for luminos."""
import luminos.luminos as luminos
import sys
import os

from PyQt5.QtCore import QProcess

RESTART_EXIT_CODE = 2

if __name__ == "__main__":
    exitCode = luminos.main()
    print("exit code", exitCode)

    if exitCode == RESTART_EXIT_CODE:
        proc = QProcess()
        proc.start(os.path.abspath(__file__))

    sys.exit(exitCode)
