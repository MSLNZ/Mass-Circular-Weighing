=============
Release Notes
=============

Version 1.1.0.dev0 (in development)
===================================

In development

Version 1.0.7 (11/05/2022)
==========================

* Fixed another bug in update status

Version 1.0.6 (11/05/2022)
==========================

* Updates status of scheme entry good runs to 0 if no file is available (but there was data previously).
* Fixed bugs from previous change to allow summary file to be used in place of the admin file

Version 1.0.5 (22/04/2022)
==========================

* Removed addition of 'Weighing Scheme' line in summary file, so that the summary file can be used in place of the
  admin file
* Added test case from TP MSLT.M.001.008 appendices C and D
* Updated docs
* Added balance serial number to measurement metadata, and program version number to analysis metadata
* Added check_serial method to identify_handler for Arduinos, using ArduinoID

Version 1.0.4 (01/02/2022)
==========================

* Revised make scripts and installs so that exe works with the circular weighing window as a subprocess
* Moved examples to utils so they are accessible from the exe

Version 1.0.3 (27/01/2022)
==========================

* Ambient monitoring NUC is now addressed by name rather than IP address
* Fixed bugs in positions setting and display
* Fixed bugs in collate_data.py for if any analysis datasets are present (even if not acceptable)
* Fixed incorrect lift positions for AT106
* Link to Commercial Calibrations folder now updates year to current year

Version 1.0.2 (04/10/2021)
==========================

* The main change is a new version of the circular weighing window without threads.
* A 'move to position' widget allows movement to any horizontal and/or lift position.
* A 'request stop' button sets bal want_abort to True, which will stop the requested action when it is safe to do so.
* A 'reconnect to balance' button reconnects to the balance and sets _want_abort to False.
* The ambient conditions are checked when connecting to the balance before the weighing window opens.
* AllocatorDialog is called from aw_carousel.py and adjust_ch box is shared between allocator and weighing windows.
* The log is saved to a .txt file when the window closes.
* The weighing process checks that the balance is initialised before commencing set of weighings and assumes it is
  initialised thereafter (to avoid retrying self-adjustment between weighings in a set).
* do_new_weighing.py has been modified to work without the gui.
* Minor changes to AT106 class: timings for internal weight loading and unloading

Version 1.0.1 (30/07/2021)
==========================

* a warning now pops up if the standard mass set is empty when being sent to the final mass calculation.
* default_admin.xlsx and default_config.xml files will be included in the installation
* balance initialisation checked before delay start for automatic weighing
* added new balance class for AT106, and modified other classes to accommodate AT106 changes
* moved all register files back to I: drive
* adjusted fields in Admin file to include more information
* run_circ_weigh.py now uses np.isclose for comparison
* adjusted tolerance for difference between 3 readings to 2.25
* changed position updating to show pos # of [#,#,...]
* subprocess.Popen used to run circular weighing in new window
* added formulae for mean and standard deviation to summary.xlsx

Version 1.0.0 (29/04/2021)
==========================

Initial release
