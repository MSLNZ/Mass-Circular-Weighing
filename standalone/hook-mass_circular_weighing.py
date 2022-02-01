"""
PyInstaller hook for Mass-Circular-Weighing
"""
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('msl.loadlib')
datas += [
    ('../mass_circular_weighing/utils/default_admin.xlsx', 'examples'),
    ('../mass_circular_weighing/utils/default_config.xml', 'examples'),
]