.. _mass-circular-weighing-welcome:

mass-circular-weighing
======================

Write the documentation for **mass-circular-weighing**.



Getting Started
---------------

To add new equipment (except balances), add the appropriate details to the `Equipment` sheet in the *Equipment Register*.
If the new equipment is a balance, add the appropriate details to the `Balances` sheet in the *Balance Register*,
and assign some initial acceptance criteria in the `AcceptanceCriteria` sheet.

Allowed weighing modes for balances are:

* mde	(manual data entry) 	no computer interface
* mw	(manual weighing) 	manually loaded, with computer interface to balance
* aw	(automatic weighing)	computer interfaces to weight changer and balance

For aw balances, enter the number of available weighing positions in the # pos column,
and the address of the weight changer (Arduino) in the WC_Address column.
Enter the Omega logger sensor in the Ambient monitoring column following the format for other entries.

.. note::
   This program does not allow for weighings using a beam balance.

To add equipment connections to a new computer, please start a new sheet for that computer in the Equipment Register
and copy the layout from another connections sheet (e.g. PDM Connections).
Please close the Register when you’ve made your changes so that it is available for others to work on.

Contents
========

.. toctree::
   :maxdepth: 2

   Install <install>
   License <license>
   Authors <authors>
   Release Notes <changelog>

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
