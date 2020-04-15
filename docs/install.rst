.. _install:

Install
=======

To install Mass-Circular-Weighing, run:

.. code-block:: console

   pip install mass-circular-weighing

Dependencies
------------
* Python 3.6+
* numpy_
* xlwt_
* comtypes_
* PyQt5_
* `MSL Package Manager`_, which is then used to install equipment, qt, loadlib, io, and network
  (all from the master branch) and their dependencies.

Other requirements
------------------
To run the program, you will need to be able to access a *Balance Register* and an *Equipment Register*
in the MSL-Equipment_ format.

   For mass calibration at MSL, these registers are stored in I:\\MSL\\Private\\MAP\\Equipment register.

To enable ambient logging via Emile's LabVIEW server, a LabVIEW Runtime engine is needed.

   At MSL, run LVRTE2010std.exe from I:\MSL\Shared\Temperature\LabVIEW RuntimeEngines.
   This install will require administrator rights on a Callaghan Innovation computer.


.. _numpy: https://www.numpy.org/
.. _xlwt: https://pypi.org/project/xlwt/
.. _comtypes: https://pypi.org/project/comtypes/
.. _PyQt5: https://pypi.org/project/PyQt5/
.. _MSL Package Manager: http://msl-package-manager.readthedocs.io/en/latest/?badge=latest
.. _MSL-Equipment: https://msl-equipment.readthedocs.io/en/latest/
