import sys, os

from msl.qt import application, QtWidgets, Button, excepthook, Logger, Slot, utils
from msl.io import read

from src.log import log
from src.constants import SW_VERSION
from src.gui.widgets.housekeeping import Housekeeping
from src.gui.widgets.scheme_table import SchemeTable
from src.gui.circweigh_popup import WeighingThread
from src.routines.run_circ_weigh import analyse_all_weighings_in_file
from src.routines.collate_data import collate_all_weighings
from src.routines.report_results import export_results_summary
from src.gui.masscalc_popup import MassCalcThread


def make_table_panel():
    check_ses = Button(text='Check scheme entries', left_click=check_scheme, )
    save_ses = Button(text='Save scheme entries', left_click=save_scheme, )
    run_row = Button(text='Do weighing(s) for selected scheme entry', left_click=collect_n_good_runs, )
    reanalyse_row = Button(text='Reanalyse weighing(s) for selected scheme entry', left_click=reanalyse_weighings, )
    update_status = Button(text='Update status', left_click=check_good_run_status, )
    collate_data = Button(text='Display collated results', left_click=display_collated)

    buttons = QtWidgets.QWidget()
    button_group = QtWidgets.QGridLayout()
    button_group.addWidget(check_ses, 0, 0)
    button_group.addWidget(save_ses, 1, 0)
    button_group.addWidget(run_row, 0, 1)
    button_group.addWidget(reanalyse_row, 1, 1)
    button_group.addWidget(update_status, 0, 2)
    button_group.addWidget(collate_data, 1, 2)
    buttons.setLayout(button_group)

    central_panel_group = QtWidgets.QGroupBox('Weighing Scheme Details')
    central_panel_layout = QtWidgets.QVBoxLayout()
    central_panel_layout.addWidget(schemetable)
    central_panel_layout.addWidget(buttons)
    central_panel_group.setLayout(central_panel_layout)

    return central_panel_group

@Slot(list)
def update_balances(bal_list):
    schemetable.update_balance_list(bal_list)

@Slot(int)
def check_good_runs_in_file(row):
    nominal = schemetable.cellWidget(row, 1).text()
    url = os.path.join(housekeeping.cfg.folder, housekeeping.cfg.client+'_'+nominal+'.json')
    if not os.path.isfile(url):
        return None

    scheme_entry = schemetable.cellWidget(row, 0).text()
    root = read(url, encoding='utf-8')

    i = 0
    good_runs = 0
    while True:
        run_id = 'run_' + str(i + 1)
        try:
            existing_mmt = root['Circular Weighings'][scheme_entry]['measurement_' + run_id]
            if existing_mmt.metadata.get('Weighing complete'):
                try:
                    existing_analysis = root['Circular Weighings'][scheme_entry]['analysis_' + run_id]
                    ok = existing_analysis.metadata.get('Acceptance met?')
                    if ok:
                        # print('Weighing accepted')
                        good_runs += 1
                    elif not existing_analysis.metadata.get['Exclude?']:
                        # print('Weighing outside acceptance but allowed')
                        good_runs += 1
                except:
                    pass
                    # print('Weighing not accepted')
        except KeyError:
            break
        i += 1

    run_1_no = int(run_id.strip('run_'))
    schemetable.update_status(row, str(good_runs)+' from '+str(run_1_no-1))

def check_good_run_status():
    for row in range(schemetable.rowCount()):
        check_good_runs_in_file(row)

def check_scheme():
    if not housekeeping.cfg.all_stds:
        housekeeping.initialise_cfg()
    schemetable.check_scheme_entries(housekeeping.cfg)

def save_scheme():
    folder = housekeeping.cfg.folder
    filename = housekeeping.cfg.client + '_Scheme.xls'
    schemetable.save_scheme(folder, filename)

def get_se_row():
    row = schemetable.currentRow()
    if row < 0:
        log.warning('No row selected')
        return None
    log.info('\nRow ' + str(row + 1) + ' selected for weighing')

    se_row_data = schemetable.get_se_row_dict(row)

    return se_row_data

def collect_n_good_runs():
    if not housekeeping.cfg.all_stds:
        housekeeping.initialise_cfg()

    se_row_data = get_se_row()

    if not se_row_data:
        return

    weigh_thread = WeighingThread()
    all_my_threads.append(weigh_thread)

    weigh_thread.weighing_done.connect(check_good_runs_in_file)
    weigh_thread.show(se_row_data, housekeeping.cfg)

def reanalyse_weighings():
    row = schemetable.currentRow()
    if row < 0:
        log.error('Please select a row')
        return

    se = schemetable.cellWidget(row, 0).text()
    nom = schemetable.cellWidget(row, 1).text()
    filename = housekeeping.cfg.client+'_'+nom

    if housekeeping.cfg.drift:
        log.info('Beginning weighing analysis using ' + housekeeping.cfg.drift + ' correction\n')
    else:
        log.info('Beginning weighing analysis using optimal drift correction\n')

    analyse_all_weighings_in_file(housekeeping.cfg, filename, se)
    check_good_runs_in_file(row)

def display_collated():
    if not housekeeping.cfg.all_stds:
        housekeeping.initialise_cfg()

    if housekeeping.cfg.all_checks is not None:
        check_wt_IDs = housekeeping.cfg.all_checks['weight ID']
    else:
        check_wt_IDs = None

    data = collate_all_weighings(schemetable, housekeeping.cfg)

    fmc_info = {'Folder': housekeeping.cfg.folder,
                'Client': housekeeping.cfg.client,
                'client_wt_IDs': housekeeping.cfg.client_wt_IDs,
                'check_wt_IDs': check_wt_IDs,
                'std_masses': housekeeping.cfg.all_stds,
                'nbc': True,
                'corr': housekeeping.cfg.correlations,
    }
    mass_thread.show(data, fmc_info)

@Slot(object)
def reporting(incl_datasets):
    if housekeeping.cfg.all_checks:
        check_set = housekeeping.cfg.all_checks['Set file']
    else:
        check_set = None
    export_results_summary(
        housekeeping.cfg,
        check_set,
        housekeeping.cfg.all_stds['Set file'],
        incl_datasets,
    )

all_my_threads = []

sys.excepthook = excepthook

# could ask user to load config file here?

gui = application()

w = QtWidgets.QWidget()
rect = QtWidgets.QDesktopWidget()
# w.setFixedSize(rect.width(), rect.height()*0.45)
w.setWindowTitle('Mass Calibration Program (version {}): Main Window'.format(SW_VERSION))

housekeeping = Housekeeping()
lhs_panel_group = housekeeping.lhs_panel_group()
schemetable = SchemeTable()
central_panel_group = make_table_panel()

housekeeping.balance_list.connect(update_balances)
schemetable.check_good_runs_in_file.connect(check_good_runs_in_file)
housekeeping.scheme_file.connect(schemetable.auto_load_scheme)

mass_thread = MassCalcThread()
mass_thread.report_summary.connect(reporting)

layout = QtWidgets.QHBoxLayout()
layout.addWidget(lhs_panel_group, 2)
layout.addWidget(central_panel_group, 5)
layout.addWidget(Logger(fmt='%(message)s'), 3)
w.setLayout(layout)
# geo = utils.screen_geometry()
# w.resize(geo.width(), geo.height() // 1.25)

w.show()
gui.exec()


def clean_up_thread(self, thread_instance):
    for i, item in enumerate(all_my_threads):
        if thread_instance is item:
            del all_my_threads[i]
            break