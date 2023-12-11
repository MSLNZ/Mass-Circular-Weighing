=============
Release Notes
=============

Version 1.0.11.dev0 (in development)
====================================

In development

Version 1.0.10 (12/12/2023)
===========================

* Initial incorporation of AX107H
* Do internal self calibration defaults to False
* Fix to parsing of weight IDs from MassRef

Version 1.0.9 (28/07/2023)
==========================

* Added excel export to test_hortres.py, where  the data from the exported Excel file is the example in the Technical
  Procedure MSLT.M.001.009. Note that the admin file was renamed in order to enable this change.
* Added direct read of chamber monitoring databases for BuildDown2023
  (Humidity and Pressure now read from Mass_Lab_Vaisala_PTU300.sqlite3;
  Temperature from Temperature_milliK.sqlite3 using calibration coefficients for 89/S4)
* Updated timestamp reporting for circweigh and info about std mass set
* Created do_repeatability functions and allowed single weight in main GUI for repeatability test
* Updated to use 'released' msl packages

Version 1.0.8 (05/09/2022)
==========================

* Fixed bug in save to C: drive in case of internet outage (for both weighing data and log file): now the weighing data
  is always saved to the C: drive and also uploaded to the I: drive if the network connection is available.
  The log file is only saved to the C: drive if the I: drive is unavailable.
* Added fix for incorrect mean and standard deviation formulae if no rows are selected in FMC
* Changed Weighing Window to automatically maximise when weighing so that the prompt windows don't cover the other info
* Allow automatic weighings to complete, even if the connection to the OMEGA logger fails, provided initial ambient
  conditions are acceptable.

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
