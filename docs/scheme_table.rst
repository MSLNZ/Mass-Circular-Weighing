.. _schemetable:

Weighing Schemes and the Scheme Table
=====================================

A weighing scheme describes the comparisons involved in a calibration,
where each comparison includes unknown and known masses.
These masses are typically client masses and reference standards respectively.
A good weighing scheme contains a minimal number of comparisons
while still providing sufficient data to assign mass values to the unknown masses, using known masses as constraints.

The Scheme Table is a container for the weighing scheme, and provides structure for the information to be collected.
Each row contains information about one comparison, for which several circular weighings (runs) may be collected.
The columns in the scheme table are:

1.  The weight groups in the order they are to be weighed in the comparison
2.  The nominal mass (in g) of a weight group in the comparison
3.  The balance 'alias' or nickname for the comparison
4.  The desired number of runs to be collected that meet the acceptance criteria
5.  The number of acceptable runs that have been collected (not editable)

Entries in these columns must follow specific formats.
For example, within a weight group individual masses are described by strings,
and multiple masses in a weight group are grouped into a weight group using '+'.
Weight groups in a comparison are separated by spaces. For example, the scheme table might look like this:

=================  ================== =================  ==================
   Weight Groups     Nominal mass (g)     Bal alias           # runs
=================  ================== =================  ==================
 200 200MA 200MB          200             AB204-S               2
 100+100MA 200MA          200             AB204-S               2
 100 100MA 100MB          100             AB204-S               2
  50+50MA 100MA           100             AB204-S               2
=================  ================== =================  ==================







