import sys
import ast

from ..log import log
from ..constants import admin_default
from ..configuration import Configuration
# from ..gui.threads.circweigh_popup import WeighingThread
from ..gui.widgets.weighing_window import WeighingWindow

# WeighingThread needs to know se_row_data, which is a dictionary of strings/integers with keys:
# ['row', 'scheme_entry', 'nominal', 'bal_alias', 'num_runs']
# It also needs a fair bit of info from the cfg object but this is harder to serialise:
# e.g. client, folder, get_bal_instance, acceptance_criteria, EXCL, timed, drift
# Instead cfg is re-created from the admin.xlsx file


def run_circweigh_popup(admin=None, se_row_data=None):
    """Runs the circular weighing pop-up window for a specified scheme entry, given the appropriate admin file

    Parameters
    ----------
    admin : path
       path to the admin.xlsx file
    se_row_data : dict
        a dictionary of strings with keys ['row', 'scheme_entry', 'nominal', 'bal_alias', 'num_runs']

    Returns
    -------
    bool on completion
    """
    from msl.qt import application, excepthook
    sys.excepthook = excepthook
    # get system arguments somehow!
    with open('circweigh_log_file.txt', 'w') as fp:
        fp.write(f"Name of the script      : {sys.argv[0]=}\n")
        fp.write(f"Arguments of the script : {sys.argv[1:]=}\n")
    try:
        if not admin:  # try using arguments from console
            admin = sys.argv[1]
        cfg = Configuration(admin)
        se_row_data = ast.literal_eval(sys.argv[2])
    except IndexError:
        pass
    except IOError as e:
        # print(f'{e.__class__.__name__}: {e}', file=sys.stderr)
        return None

    if not admin:  # prompt user for input
        if admin is None:
            admin = input("Please enter the path to the admin.xlsx file or press enter to use default.")
            print(admin)
        if admin is None:
            admin = admin_default
            print(admin)
        try:
            cfg = Configuration(admin)
            default = input("Press enter to continue")  # needed in case config pop-up appears - can't use this catch with subprocess
        except IOError as e:
            print(f'{e.__class__.__name__}: {e}', file=sys.stderr)
            return None

    if se_row_data is None:
        se_row_data = {'row': 0}
        se_row_data['bal_alias'] = input("Please enter the balance alias")
        se_row_data['scheme_entry'] = input("Please enter the scheme entry")
        se_row_data['nominal'] = input("Please enter the nominal mass")
        se_row_data['num_runs'] = input("Please enter the target number of good runs")

    gui = application()

    w = WeighingWindow()
    w.show(se_row_data, cfg)

    gui.exec()




