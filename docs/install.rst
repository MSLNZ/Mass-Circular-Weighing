Install
=======

To install Mass-Circular-Weighing, run:

.. code-block:: console

   pip install mass-circular-weighing

Dependencies
------------
* Python 3.6 or 3.7.  To use Python 3.8, `Python for .NET`_ will need to be installed separately.
* numpy_
* xlwt_
* comtypes_
* PyQt5_
* `Python for .NET`_
* `MSL Package Manager`_, which is then used to install equipment, qt, loadlib, io, and network
  (all from the master branch) and their dependencies.

Other requirements
------------------
To run the program, you will need to be able to access a *Balance Register* and an *Equipment Register*
in the MSL-equipment format.

.. Note::
   For mass calibration at MSL, these registers are stored in I:\\MSL\\Private\\MAP\\Equipment register.

To enable ambient logging via Emile's LabVIEW server, a LabVIEW Runtime engine is needed.

.. Note::
   At MSL, run LVRTE2010std.exe from I:\MSL\Shared\Temperature\LabVIEW RuntimeEngines.
   This install will require administrator rights on a Callaghan Innovation computer.


.. _numpy: https://www.numpy.org/
.. _xlwt: https://pypi.org/project/xlwt/
.. _comtypes: https://pypi.org/project/comtypes/
.. _PyQt5: https://pypi.org/project/PyQt5/
.. _Python for .NET: https://pypi.org/project/pythonnet/
.. _MSL Package Manager: http://msl-package-manager.readthedocs.io/en/latest/?badge=latest
