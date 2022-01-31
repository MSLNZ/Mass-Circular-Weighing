@ECHO off
python -c "import sys; print(sys.executable)"
python -m PyInstaller --clean --noconfirm --additional-hooks-dir . mass_circular_weighing_standalone.py --hidden-import PyQt5 ^
--hidden-import PyQt5.QtGui --hidden-import PyQt5.QtWidgets --hidden-import PyQt5.QtSvg --hidden-import QtCore.Qt --hidden-import sqlite3