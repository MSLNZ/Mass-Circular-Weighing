import os
import numpy as np
import pytest

from msl.io import JSONWriter, read

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
jsonfile_for_test = os.path.join(ROOT_DIR, r'tests\samples\BuildUp_50kg_20000.json')


def check_remove(url=jsonfile_for_test, se="20KRA 10KMA+10KMB 20KRB 20KRC"):
    # print(url)
    i = 1
    while True:
        try:
            run_id = 'run_' + str(i)

            read_root = read(url, encoding='utf-8')
            read_root.read_only = True
            root = JSONWriter()
            root.set_root(read_root)
            root.read_only = True

            schemefolder = root['Circular Weighings'][se]
            analysis = schemefolder['analysis_' + run_id]  # so that it breaks out of the loop when no more run_id's
            assert repr(root) == "<JSONWriter 'NoneType' (5 groups, 10 datasets, 0 metadata)>"

            se_name = '/Circular Weighings/' + se + '/analysis_' + run_id
            # a = root.remove(schemefolder.name + '/analysis_' + run_id)

            with pytest.raises(ValueError) as err:
                root.remove(se_name)
            assert "Cannot modify" in str(err.value)
            assert repr(root) == "<JSONWriter 'NoneType' (5 groups, 10 datasets, 0 metadata)>"

            root.read_only = False
            a = root.remove(se_name)

            if url.split("\\")[-1] == "BuildUp_50kg_20000.json":
                if i == 1:
                    b = np.array([
                        ('20KRA', '10KMA+10KMB',  0.0146875 , 0.0070841 ),
                        ('10KMA+10KMB', '20KRB', -0.01197917, 0.0070841 ),
                        ('20KRB', '20KRC', -0.01197917, 0.0070841 ),
                        ('20KRC', '20KRA',  0.00927083, 0.00740505)
                    ],
                    dtype=[('+ weight group', 'O'), ('- weight group', 'O'), ('mass difference', '<f8'), ('residual', '<f8')])

                else:
                    b = np.array([('20KRA', '10KMA+10KMB', 0.02647183, 0.00358727),
                        ('10KMA+10KMB', '20KRB', -0.00710593, 0.00355523),
                        ('20KRB', '20KRC', -0.01686143, 0.00358727),
                        ('20KRC', '20KRA', -0.00250447, 0.00416776)
                    ],
                    dtype=[('+ weight group', 'O'), ('- weight group', 'O'), ('mass difference', '<f8'), ('residual', '<f8')])

                for row in range(4):
                    assert a[row][2] == pytest.approx(b[row][2])

            assert repr(root) == "<JSONWriter 'NoneType' (5 groups, 9 datasets, 0 metadata)>"

            i += 1

        except KeyError:
            # print('No more runs to analyse\n')
            break




""" Here are the other scheme entries in the file:
scheme_entries = [
    "20KRA 10KMA+10KMB 20KRB 20KRC",
    "20KRB 10KMA+10KMB 20KRC 20KRD",
    "20KRC 10KMA+10KMB 20KRD 20KRA",
    "20KRD 10KMA+10KMB 20KRA 20KRB",
]

se = scheme_entries[0]  # play with 0 - 3 here
"""

if __name__ == '__main__':
    check_remove()

