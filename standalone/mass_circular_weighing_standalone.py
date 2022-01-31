import sys
import traceback

try:
    from mass_circular_weighing.gui import gui

    # Show the GUI
    gui.show_gui()

except KeyboardInterrupt:
    pass

except:
    traceback.print_exc(file=sys.stderr)
    input('Press <ENTER> to close ...')
