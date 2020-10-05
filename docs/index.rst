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

1. :ref:`install` the program or download the repository
2. Run show-gui (or run the executable version)
3. Load a *config.xml* file and/or edit the example config file using the edit config button

        For each calibration, a *config.xml* file is needed which follows the format described in MSL-Equipment_.
        This file holds important information such as
        where to find the equipment register(s),
        which balances and standard mass sets are available,
        limits on ambient conditions,
        and 'housekeeping' details for the particular calibration (job number, client, client masses etc).
        More information about the *config.xml* file is provided under :ref:`configfile`.

4. Decide on a weighing scheme and either enter it manually into the :ref:`schemetable`
   or load it from an Excel file by drag-drop into the table.
5. Check that the scheme entries have been entered using the same weight IDs as in the weight sets
6. Save the scheme
7. Do circular weighings for each scheme entry, following the prompts that appear
8. Run the final mass calculation to determine mass values for each of the unknown masses
9. Check that the mass values make sense
10. Export a summary file (of all the data, both raw from circular weighings and analysis data)


Contents
========

.. toctree::
   :maxdepth: 2

   Install <install>
   Equipment Registers <equip_registers>
   Configuration File <configfile>
   Scheme Table <scheme_table>
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
