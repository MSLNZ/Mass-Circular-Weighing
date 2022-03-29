.. _registers:

Equipment Registers
===================

The :ref:`mass-circular-weighing-welcome` program is built using Joe Borbely's MSL packages,
in particular MSL-Equipment_, for consistency in programming across MSL (and because it's awesome).
MSL-Equipment_ uses equipment registers to keep track of information about the
equipment in use, and how each computer connects to the equipment.
More information about these two different types of `Database Formats`_ can be found in
`Equipment-Register Database`_ and `Connections Database`_ respectively.

The registers relevant for this program are the *Balance Register* and the *Equipment Register*.

    The Mass Standards registers are stored on the I: drive in I:\\MSL\\Private\\Mass\\Equipment Register.

To add new equipment (except balances), add the appropriate details to the `Equipment` sheet in the *Equipment Register*.

If the new equipment is a balance, add the appropriate details to the `Balances` sheet in the *Balance Register*,
and assign some initial acceptance criteria in the `AcceptanceCriteria` sheet.

Allowed weighing modes for balances are:

* **mde**	(manual data entry)
    for any balance that is manually loaded and manually read (i.e. no computer interface)
* **mw**	(manual weighing)
    for Mettler Toledo balances that have a computer interface to the balance but are manually loaded
* **aw_c**	(automatic weighing, circular carousel)
    for Mettler Toledo balances that have a computer interface to the balance
    and an in-built carousel weight changer for automatic weight loading
* **aw_l**	(automatic weighing, linear carriage)
    for Mettler Toledo balances that have a computer interface to the balance
    and a custom-built linear weight changer for automatic weight loading

For **aw** balances, enter the number of available weighing positions in the # pos column.
For **aw_l** balances, also enter the name of the weight changer (e.g. Arduino) in the Handler column.

*This program does not allow for weighings using a beam balance.*

Enter the ambient monitoring sensor name following the format for other entries.

To add information about connections to a computer for any type of equipment,
please start a new sheet for that computer in the *Equipment Register*
and copy the layout from another connections sheet.

Please close the *Register* when you've made your changes so that it is available for others to work on.


.. _MSL-Equipment:  https://msl-equipment.readthedocs.io/en/latest/index.html
.. _Database Formats: https://msl-equipment.readthedocs.io/en/latest/database.html#database-formats
.. _Equipment-Register Database: https://msl-equipment.readthedocs.io/en/latest/database.html#equipment-database
.. _Connections Database: https://msl-equipment.readthedocs.io/en/latest/database.html#connections-database