"""
PyInstaller hook for Mass-Circular-Weighing
"""
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('msl.loadlib')
datas += [('../examples/sample_config.xml', 'examples')]
