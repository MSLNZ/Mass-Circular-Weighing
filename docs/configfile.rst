.. _configfile:

The Configuration File
======================

The :ref:`mass-circular-weighing-welcome` program uses Joe Borbely's MSL packages, in particular MSL-Equipment_,
and so a *config.xml* file is needed for each circular weighing, as described in `Configuration File`_.

As well as specifying the relevant equipment register(s), this *config.xml* file also keeps a record of
which balances are available, and limits on ambient conditions.

To set up a *config.xml* file for the :ref:`mass-circular-weighing-welcome` program, a template is provided below
with some explanation of the structure and tags.  The following sample *config.xml* file can also be found in
mass_circular_weighing/utils/default_config.xml.

.. code-block:: xml

    <?xml version="1.0" encoding="utf-8"?>
      <msl>

        <!-- Specify all balances available for weighings. Details here must match the Balance register entries -->
        <equipment alias="MDE-demo" manufacturer="Mettler Toledo" model="TEST_BAL"/>
        <equipment alias="AW-demo" manufacturer="Mettler Toledo" model="Test_AW"/>
        <equipment alias="K_C" manufacturer="Mettler Toledo" model="XPR604"/>
        <equipment alias="LUCY" manufacturer="Mettler Toledo" model="XPR64002LC"/>
        <equipment alias="AX10005" manufacturer="Mettler Toledo" model="AX10005"/>
        <equipment alias="AX1006" manufacturer="Mettler Toledo" model="AX1006"/>
        <equipment alias="CCE605" manufacturer="Sartorius" model="CCE605"/>
        <equipment alias="XPE505C" manufacturer="Mettler Toledo" model="XPE505C"/>
        <equipment alias="AB204-S" manufacturer="Mettler Toledo" model="AB204-S"/>
        <equipment alias="AT106" manufacturer="Mettler Toledo" model="AT106"/>
        <equipment alias="XPR6U" manufacturer="Mettler Toledo" model="XPR6U"/>
        <equipment alias="UMX5" manufacturer="Mettler Toledo" model="UMX5"/>

        <!-- Specify Arduino information -->
        <equipment alias="Arduino-XPE505C" manufacturer="Arduino" model="MEGA2560" serial="95730333238351F0A011"/>
        <equipment alias="Arduino-AT106" manufacturer="Arduino" model="MEGA2560" serial="5573132313635190E1B1"/>

        <!-- Specify Vaisala ambient monitoring equipment available for weighings. -->
        <equipment alias="AX10005-Vaisala-K1510011" manufacturer="Vaisala" model="PTU303" serial="K1510011"/>
        <equipment alias="AX1006-Vaisala-M2430306" manufacturer="Vaisala" model="PTU303" serial="M2430306"/>

        <!-- Specify the limits for ambient conditions to begin weighing. -->
        <min_temp units="C">18.1</min_temp>
        <max_temp units="C">21.9</max_temp>
        <min_rh units="%">30</min_rh>
        <max_rh units="%">70</max_rh>

        <!-- Specify the limits for changes in ambient conditions during weighing. -->
        <max_temp_change units="C">0.5</max_temp_change>
        <max_rh_change units="%">15</max_rh_change>

        <!-- Specify where to find acceptance limits for circular weighing data.
        (i.e. specify the path to the Balance register, which should not change) -->
        <acceptance_criteria>
              <path>I:\MSL\Private\Mass\Equipment Register\Balance register.xlsx</path>
              <sheet>AcceptanceCriteria</sheet>
              <EXCL>3</EXCL> <!-- criterion for excluding a single weighing within an automatic weighing sequence
                                from the final averaging (and from any tally of happy weighings).
                                Currently set to a rather arbitrary value without any experimental basis... -->
        </acceptance_criteria>

        <!-- Specify the Equipment-Register Databases to load equipment records from.
        As for the acceptance criteria, the path to the Balance register and Equipment register should not change,
        nor should the sheet names. -->
        <registers>
          <register
                  team="M&amp;P"
                  user_defined="unit, ambient_monitoring, weighing_mode, stable_wait, resolution, pos, handler">
              <path>I:\MSL\Private\Mass\Equipment Register\Balance register.xlsx</path>
              <sheet>Balances</sheet>
          </register>

          <register team="M&amp;P">
              <path>I:\MSL\Private\Mass\Equipment Register\Balance register.xlsx</path>
              <sheet>AuxiliaryEquip</sheet>
          </register>
        </registers>

        <!-- Specify the Connections Databases to load connection records from.
        (The path is likely to be the same as the Equipment register above)
        Make sure to specify the correct sheet for the computer in use -->
        <connections>
          <connection>
            <path>I:\MSL\Private\Mass\Equipment Register\Connections register.xlsx</path>
            <sheet>(will be replaced by os.environ['COMPUTERNAME'])</sheet>
          </connection>
        </connections>

      </msl>



.. _MSL-Equipment:  https://msl-equipment.readthedocs.io/en/latest/index.html
.. _Configuration File: https://msl-equipment.readthedocs.io/en/latest/config.html#configuration-file

