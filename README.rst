Mass-Circular-Weighing
======================

**Mass-Circular-Weighing** is a Python program designed to assist with
the calibration of masses at the Measurement Standards Laboratory of New Zealand.
Weighings are performed using the method of circular weighing described in
`A general approach to comparisons in the presence of drift
<https://www.callaghaninnovation.govt.nz/general-approach-comparisons-presence-drift>`_.


Install
-------

To install Mass-Circular-Weighing, first install `MSL Package Manager`_,
then use the Package Manager to install Mass-Circular-Weighing:

.. code-block:: console

   pip install msl-package-manager
   msl install mass-circular-weighing

These two commands should install the program and all its dependencies as needed.

Dependencies
++++++++++++
* Python 3.6+
* `MSL Package Manager`_, which is then used to install msl packages
  (equipment, qt, loadlib, io, and network) and their dependencies.
* PyQt5_ is needed for msl-qt (see msl-qt_ for how to install PyQt5 with msl-qt)
* numpy_ and xlrd_ are included in the msl packages
* requests_ is needed to communicate with the Omega ambient monitoring web server
* xlwt_, and openpyxl_ are used for Excel file handling
* tabulate_ is used for LaTeX output

Other requirements
------------------

To run the program, you will need to be able to access the *Balance Register* and the *Equipment Register*
in G:\Shared drives\MSL - MAP\Equipment register.

Documentation
-------------
The documentation for **Mass-Circular-Weighing** can be found here_.

.. _MSL Package Manager: http://msl-package-manager.readthedocs.io/en/latest/?badge=latest
.. _msl-qt: https://github.com/MSLNZ/msl-qt
.. _PyQt5: https://pypi.org/project/PyQt5/
.. _numpy: https://www.numpy.org/
.. _xlrd: https://pypi.org/project/xlrd/
.. _requests: https://requests.readthedocs.io/en/master/index.html
.. _xlwt: https://pypi.org/project/xlwt/
.. _openpyxl: https://pypi.org/project/openpyxl/
.. _tabulate: https://pypi.org/project/tabulate/

.. _here: https://github.com/MSLNZ/Mass-Circular-Weighing/blob/main/docs/index.rst
