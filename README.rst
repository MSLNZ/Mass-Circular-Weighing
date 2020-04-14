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

To run the program, you will need to be able to access the *Balance Register* and the *Equipment Register*
which are stored on the I: drive in `I:\\MSL\\Private\\MAP\\Equipment register`.




Documentation
-------------
The documentation for **Mass-Circular-Weighing** can be found `here` (link to be added).


.. _numpy: https://www.numpy.org/
.. _xlwt: https://pypi.org/project/xlwt/
.. _comtypes: https://pypi.org/project/comtypes/
.. _PyQt5: https://pypi.org/project/PyQt5/
.. _Python for .NET: https://pypi.org/project/pythonnet/
.. _MSL Package Manager: http://msl-package-manager.readthedocs.io/en/latest/?badge=latest