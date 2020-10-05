Mass-Circular-Weighing
======================

**Mass-Circular-Weighing** is a Python program designed to assist with
the calibration of masses at the Measurement Standards Laboratory of New Zealand.
Weighings are performed using the method of circular weighing described in
`A general approach to comparisons in the presence of drift
<https://www.callaghaninnovation.govt.nz/general-approach-comparisons-presence-drift>`_.



Install
-------

To install Mass-Circular-Weighing, run:

.. code-block:: console

   pip install mass-circular-weighing

Dependencies
++++++++++++
* Python 3.6+
* numpy_
* xlwt_, xlrd_ and openpyxl_
* comtypes_
* tabulate_ (for LaTeX output)
* PyQt5_
* `MSL Package Manager`_, which is then used to install msl packages (equipment, qt, loadlib, io, and network,
all from the master branch) and their dependencies.

Other requirements
------------------

To run the program, you will need to be able to access the *Balance Register* and the *Equipment Register*
which are stored on the I: drive in I:\\MSL\\Private\\MAP\\Equipment register.

To enable ambient logging (e.g. of Omega loggers) via Emile's LabVIEW server, run LVRTE2010std.exe from
I:\MSL\Shared\Temperature\LabVIEW RuntimeEngines.
This install will require administrator rights on a Callaghan Innovation computer.



Documentation
-------------
The documentation for **Mass-Circular-Weighing** can be found here_.


.. _numpy: https://www.numpy.org/
.. _xlwt: https://pypi.org/project/xlwt/
.. _xlrd: https://pypi.org/project/xlrd/
.. _openpyxl: https://pypi.org/project/openpyxl/
.. _comtypes: https://pypi.org/project/comtypes/
.. _tabulate: https://pypi.org/project/tabulate/
.. _PyQt5: https://pypi.org/project/PyQt5/
.. _MSL Package Manager: http://msl-package-manager.readthedocs.io/en/latest/?badge=latest
.. _here: https://github.com/MSLNZ/Mass-Circular-Weighing/blob/master/docs/index.rst