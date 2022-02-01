import sys
import traceback

nargs = len(sys.argv)

try:
    if nargs == 1:      # Show the GUI
        from mass_circular_weighing.gui import gui
        gui.show_gui()
    elif nargs == 3:    # Show the weighing window
        from mass_circular_weighing.utils.circweigh_subprocess import run_circweigh_popup
        run_circweigh_popup()
    else:               # Something has gone wrong...
        raise ValueError(f'Invalid number of command line arguments: {nargs}')

except KeyboardInterrupt:
    pass

except:
    traceback.print_exc(file=sys.stderr)
    input('Press <ENTER> to close ...')
