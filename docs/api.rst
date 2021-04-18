.. _mcw-api:

=================
API Documentation
=================

The main entryway in to **Mass-Circular-Weighing** is achieved by running the gui, as in the following example:

.. code-block:: pycon

    >>> import mass_circular_weighing as mcw  # doctest: +SKIP
    >>> mcw.show_gui()  # doctest: +SKIP

The program can also be used to quickly check ambient conditions by connecting to the omega logger server:

.. code-block:: pycon

    >>> import mass_circular_weighing as mcw  # doctest: +SKIP
    >>> mcw.poll_omega_logger('mass 1')  # doctest: +SKIP

Connection to a balance is also possible without running the gui:

.. code-block:: pycon

    >>> import mass_circular_weighing as mcw  # doctest: +SKIP
    >>> bal = mcw.find_balance(bal_alias='MDE-demo')  # doctest: +SKIP

if the balance alias is known, or

.. code-block:: pycon

    >>> import mass_circular_weighing as mcw  # doctest: +SKIP
    >>> bal = mcw.find_balance()  # doctest: +SKIP

if the balance alias is unknown; the latter will print a list of known balances,
and prompt the user to enter the alias of the balance to connect with.

