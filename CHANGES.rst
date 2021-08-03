=============
Release Notes
=============

Version 1.0.2 (in development)
==============================

In development.

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
