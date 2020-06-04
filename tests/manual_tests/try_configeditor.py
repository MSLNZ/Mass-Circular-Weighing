import sys
from msl.qt import application, excepthook


sys.excepthook = excepthook

gui = application()

#Version 1:
from mass_circular_weighing.gui.widgets.config_editor import ConfigEditor
widgey = ConfigEditor()
widgey.show()

gui.exec()

cfg = widgey.new_config
print(cfg)


# Version 2:
"""
from mass_circular_weighing.gui.threads.configedit_thread import ConfigEditorThread

cfe = ConfigEditorThread()

cfe.show("")

print(cfe.wait_for_prompt_reply())

gui.exec()
"""
