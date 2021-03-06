.. _configfile:

The Configuration File
======================

The :ref:`mass-circular-weighing-welcome` program uses Joe Borbely's MSL packages, in particular MSL-Equipment_,
and so a *config.xml* file is needed for each circular weighing, as described in `Configuration File`_.

As well as specifying the relevant equipment register(s), this *config.xml* file also keeps a record of
which balances and standard mass sets are available, limits on ambient conditions,
and 'housekeeping' details for the particular calibration (job number, client, client masses etc).

To set up a *config.xml* file for the :ref:`mass-circular-weighing-welcome` program, a template is provided below
with some explanation of the structure and tags.  A sample *config.xml* file can be found in examples/sample_config.xml.


.. code-block:: xml

    <?xml version="1.0" encoding="utf-8"?>
      <msl>

        <!-- Specify client-specific information. -->
        <save_folder>I:\MSL\Private\Mass\Sample Data\Job</save_folder>
        <!-- The parent folder in which all data and analysis files are saved -->
        <job>job</job>
        <!-- The MSL job code for the calibration -->
        <client>client</client>
        <!-- The name of the client. Files will be created with this name inside the parent folder during the calibration process -->
        <client_masses>1 2 5 10 20 50 100 200 500 1000 2000 5000 10000</client_masses>
        <!-- A list of client masses separated only by spaces, in any order -->
        <std_set>MET19A</std_set>
        <!-- The reference set used as standards in the weighing scheme.
        Use tags of sets as in <standards> below. -->
        <check_set>MET19B</check_set>
        <!-- The reference set used as checks in the weighing scheme.
        Use tags of sets as in <standards> below, or None. -->
        <drift>auto select</drift>
        <!-- Specify a drift option to use in the least squares analysis of each circular weighing.
        Allowed options: auto select, linear drift, quadratic drift, cubic drift -->
        <use_times>NO</use_times>
        <!-- Specify whether to use the recorded times for each mass measurement in the least squares analysis of each circular weighing.
        Allowed options: YES or NO -->
        <correlations>None</correlations>
        <!-- If relevant, include a matrix/list of correlations between standards (e.g. in build-up or build-down).
        Allowed options: None, or matrix of correlations-->

        <!-- Specify all balances available for weighings. Details here must match the Balance register entries -->
        <equipment alias="MDE-demo" manufacturer="Mettler Toledo" model="TEST_BAL"/>
        <equipment alias="AW-demo" manufacturer="Mettler Toledo" model="Test_AW"/>

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
              <path>I:\MSL\Private\MAP\Equipment register\Balance register.xlsx</path>
              <sheet>AcceptanceCriteria</sheet>
              <EXCL>3</EXCL> <!-- criterion for excluding a single weighing within an automatic weighing sequence
                                from the final averaging (and from any tally of happy weighings).
                                Currently set to a rather arbitrary value without any experimental basis... -->
        </acceptance_criteria>

        <!-- Specify all standard sets available for weighing analysis using individual tags such as <MET19A>.
        Whichever tags are used here must also be used when specifying the std_set and check_set.. -->
        <standards>
              <MET19A>I:\MSL\Private\Mass\Sample Data\MET19A.set</MET19A>
              <MET19B>I:\MSL\Private\Mass\Sample Data\MET19B.set</MET19B>
              <MET16A>I:\MSL\Private\Mass\Sample Data\MET16A.set</MET16A>
              <MET16B>I:\MSL\Private\Mass\Sample Data\MET16B.set</MET16B>
              <CUSTOM>I:\MSL\Private\Mass\Sample Data\CUSTOM.set</CUSTOM>
        </standards>

        <!-- Specify the Equipment-Register Databases to load equipment records from.
        As for the acceptance criteria, the path to the Balance register and Equipment register should not change,
        nor should the sheet names. -->
        <registers>
          <register
                  team="M&amp;P"
                  user_defined="unit, ambient_monitoring, weighing_mode, stable_wait, resolution, pos, address">
              <path>I:\MSL\Private\MAP\Equipment register\Balance register.xlsx</path>
              <sheet>Balances</sheet>
          </register>

          <register team="M&amp;P">
              <path>I:\MSL\Private\MAP\Equipment register\Equipment register.xlsx</path>
              <sheet>Equipment</sheet>
          </register>
        </registers>

        <!-- Specify the Connections Databases to load connection records from.
        (The path is likely to be the same as the Equipment register above)
        Make sure to specify the correct sheet for the computer in use -->
        <connections>
          <connection>
            <path>I:\MSL\Private\MAP\Equipment register\Equipment register.xlsx</path>
            <sheet>LenovoX260</sheet>
          </connection>
        </connections>

      </msl>



.. _MSL-Equipment:  https://msl-equipment.readthedocs.io/en/latest/index.html
.. _Configuration File: https://msl-equipment.readthedocs.io/en/latest/config.html#configuration-file

