.. _mcw-api:

=================
API Documentation
=================

The main entryway in to **Mass-Circular-Weighing** is achieved by running the gui, as in the following example:

.. code-block:: pycon

    >>> import mass_circular_weighing as mcw
    >>> mcw.show_gui()

The program can also be used to quickly check ambient conditions by connecting to the omega logger server:

.. code-block:: pycon

    >>> import mass_circular_weighing as mcw
    >>> mcw.poll_omega_logger('mass 1')

Connection to a balance is also possible without running the gui:

.. code-block:: pycon

    >>> import mass_circular_weighing as mcw
    >>> bal = mcw.find_balance(bal_alias='MDE-demo')

if the balance alias is known, or

.. code-block:: pycon

    >>> import mass_circular_weighing as mcw
    >>> bal = mcw.find_balance()

if the balance alias is unknown; the latter will print a list of known balances,
and prompt the user to enter the alias of the balance to connect with.

