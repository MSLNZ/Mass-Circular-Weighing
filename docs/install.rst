.. _install:

Install
=======

To install **Mass-Circular-Weighing**, first install `MSL Package Manager`_,
then use the Package Manager to install **Mass-Circular-Weighing**:

.. code-block:: console

   pip install msl-package-manager
   msl install mass-circular-weighing

These two commands should install the program and all its dependencies as needed.

Dependencies
------------
* Python 3.6+
* numpy_
* xlwt_, xlrd_ and openpyxl_
* comtypes_
* tabulate_ (for LaTeX output)
* PyQt5_
* `MSL Package Manager`_, which can be used to install msl-equipment, -qt, -loadlib, -io, and -network,
  and any dependencies.

Other requirements
------------------
To run the program, you will need to be able to access a *Balance Register* and an *Equipment Register*
in the MSL-Equipment_ format.

   For mass calibration at MSL, these registers are stored in I:\\MSL\\Private\\Mass\\Equipment register.



.. _numpy: https://www.numpy.org/
.. _xlwt: https://pypi.org/project/xlwt/
.. _xlrd: https://pypi.org/project/xlrd/
.. _openpyxl: https://pypi.org/project/openpyxl/
.. _comtypes: https://pypi.org/project/comtypes/
.. _tabulate: https://pypi.org/project/tabulate/
.. _PyQt5: https://pypi.org/project/PyQt5/
.. _MSL Package Manager: http://msl-package-manager.readthedocs.io/en/latest/?badge=latest
.. _MSL-Equipment: https://msl-equipment.readthedocs.io/en/latest/