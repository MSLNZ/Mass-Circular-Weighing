.. _registers:

Equipment Registers
===================

The **Mass-Circular-Weighing** program is built using `MSL-equipment`, and so relies on equipment registers in the format
described in `<ref to equipment registers page>`.

The registers relevant for this program are the *Balance Register* and the *Equipment Register*
that are stored on the I: drive in I:\\MSL\\Private\\MAP\\Equipment register.

To add new equipment (except balances), add the appropriate details to the `Equipment` sheet in the *Equipment Register*.
If the new equipment is a balance, add the appropriate details to the `Balances` sheet in the *Balance Register*,
and assign some initial acceptance criteria in the `AcceptanceCriteria` sheet.

Allowed weighing modes for balances are:

* **mde**	(manual data entry)
  for balances that are manually loaded and manually read (i.e. it has no computer interface)
* **mw**	(manual weighing)
  for balances that have a computer interface to the balance but are manually loaded
* **aw**	(automatic weighing)
  for balances that have a computer interface to the balance
  and also to a weight changer for automatic weight loading

.. note::
   This program does not allow for weighings using a beam balance.

For **aw** balances, enter the number of available weighing positions in the # pos column,
and the address of the weight changer (Arduino) in the WC_Address column.

Enter the Omega logger sensor in the Ambient monitoring column following the format for other entries.

To add equipment connections to a new computer, please start a new sheet for that computer in the Equipment Register
and copy the layout from another connections sheet (e.g. PDM Connections).
Please close the *Register* when you’ve made your changes so that it is available for others to work on.