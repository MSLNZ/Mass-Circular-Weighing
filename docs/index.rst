.. _mass-circular-weighing-welcome:

Mass-Circular-Weighing
======================

**Mass-Circular-Weighing** is a Python program intended for the calibration of masses
at the Measurement Standards Laboratory of New Zealand.
Weighings are performed using the method of circular weighing described in
`A general approach to comparisons in the presence of drift
<https://www.callaghaninnovation.govt.nz/general-approach-comparisons-presence-drift>`_.

The program is designed to guide an operator through a mass calibration using electronic balances with or without
automatic weight changers.  This program does not allow for weighings using a beam balance.


Getting Started
---------------
Here's a quick list of the steps in the program.
More information about the various parts of the program are provided in the links.

1. :ref:`install` the program or clone the repository, or download the executable. Run the executable directly, or in
   Python, run

.. code-block:: pycon

   >>> import mass_circular_weighing as mcw  # doctest: +SKIP
   >>> mcw.show_gui()  # doctest: +SKIP

2. Prepare your *admin.xlsx* file and *config.xml* file

        For each calibration, an *admin.xlsx* file is needed, as described in :ref:`adminfile`. This file contains
        'housekeeping' details for the particular calibration (job number, client, client masses etc) along with the
        weighing scheme.

        For each calibration, a *config.xml* file is needed which follows the format described in MSL-Equipment_.
        This file holds information such as where to find the equipment register(s), which balances are available,
        and limits on acceptable ambient conditions.  More information about the *config.xml* file is provided under
        :ref:`configfile`.

3.  Load the *admin.xlsx* file e.g. by drag-drop onto the browse box or by using the browse button (open folder icon).

4.	Check that the details that have been loaded in the Housekeeping panel are correct. Make any corrections in the
        Admin file and reload as necessary. Click **Confirm settings** when all details are correct.

5.	Check that the weighing scheme has loaded correctly from the Scheme sheet of the Admin file. If the names of any
        balances were not the correct alias, the field will appear blank.  Use the drop-down menu to select the correct
        balance.

            Alternatively, enter the scheme manually into the Scheme Table following the guidance in :ref:`schemetable`.

6.	Press **Check scheme entries** to check that the scheme uses the same weight IDs as in the specified weight sets

7.	Press **Save scheme entries** to save any changes entered in the GUI to a scheme file (naming convention is
        Client_Scheme.xls) in the appropriate folder.

            Using **Save scheme entries** also guarantees the program will be able to find the scheme file later.

8.	To do a weighing, click somewhere in the row for the corresponding scheme entry. Press **Do weighing(s) for selected
        scheme entry** to initiate circular weighings for that scheme entry.

9.	Follow the prompts that appear to do the weighing

10.	Repeat the previous two steps until all weighings are completed

11.	Press **Display collated results** to open the final mass calculation window

12.	Click **Do calculation** to run the final mass calculation to determine mass values for each of the unknown masses

13.	Check that the mass values make sense

14.	Click **Export all results to summary file** to save the results and data to summary files



Contents
========

.. toctree::
   :maxdepth: 2

   Install <install>
   Equipment Registers <equip_registers>
   Admin File <adminfile>
   Configuration File <configfile>
   Scheme Table <scheme_table>
   API Documentation <api>
   License <license>
   Authors <authors>
   Release Notes <changelog>

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _MSL-Equipment: https://msl-equipment.readthedocs.io/en/latest/
.. _useful-RST-tips: https://docutils.sourceforge.io/docs/user/rst/quickref.html#escaping
