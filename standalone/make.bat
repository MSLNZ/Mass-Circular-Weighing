@ECHO off
pyinstaller --clean --noconfirm --additional-hooks-dir . mass_circular_weighing_standalone.py
