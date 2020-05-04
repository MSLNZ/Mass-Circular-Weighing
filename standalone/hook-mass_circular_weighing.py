"""
PyInstaller hook for Mass-Circular-Weighing
"""
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('msl.loadlib')
datas += [('../mass_circular_weighing/equip/labenviron_dll.py', 'mass_circular_weighing/equip')]
datas += [('../mass_circular_weighing/resources/LabEnviron_V1.3.dll', 'mass_circular_weighing/resources')]
datas += [('../examples/sample_config.xml', 'examples')]
