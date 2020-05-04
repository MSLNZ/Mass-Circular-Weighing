from mass_circular_weighing.gui import gui
from mass_circular_weighing.routines.run_circ_weigh import dll

# Show the GUI
gui.show_gui()

# NOTE: This is a hack. Shutting down LabEnviron32 should happen
# automatically when the GUI closes -- but it doesn't.
dll.shutdown_server32()
