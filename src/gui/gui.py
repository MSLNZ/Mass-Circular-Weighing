import sys

from msl.qt import application, QtWidgets, Button, excepthook, Logger

from src.log import log
from src.gui.widgets.housekeeping import Housekeeping
from src.gui.widgets.scheme_table import SchemeTable
from src.gui.circweigh_popup import WeighingThread
from src.routines.run_circ_weigh import analyse_all_weighings_in_file
from src.routines.collate_data import collate_all_weighings
from src.gui.masscalc_popup import MassCalcThread


def make_table_panel():
    check_ses = Button(text='Check scheme entries', left_click=check_scheme, )
    save_ses = Button(text='Save scheme entries', left_click=save_scheme, )
    run_row = Button(text='Do weighing(s) for selected scheme entry', left_click=collect_n_good_runs, )
    reanalyse_row = Button(text='Reanalyse weighing(s) for selected scheme entry', left_click=reanalyse_weighings, )
    display_data = Button(text='Display selected weighing', left_click=display_se_results, )
    collate_data = Button(text='Display collated results', left_click=display_collated)

    buttons = QtWidgets.QWidget()
    button_group = QtWidgets.QGridLayout()
    button_group.addWidget(check_ses, 0, 0)
    button_group.addWidget(save_ses, 1, 0)
    button_group.addWidget(run_row, 0, 1)
    button_group.addWidget(reanalyse_row, 1, 1)
    button_group.addWidget(display_data, 0, 2)
    button_group.addWidget(collate_data, 1, 2)
    buttons.setLayout(button_group)

    central_panel_group = QtWidgets.QGroupBox('Weighing Scheme Details')
    central_panel_layout = QtWidgets.QVBoxLayout()
    central_panel_layout.addWidget(schemetable)
    central_panel_layout.addWidget(buttons)
    central_panel_group.setLayout(central_panel_layout)

    return central_panel_group


def check_scheme():
    schemetable.check_scheme_entries(housekeeping)

def save_scheme():
    folder = housekeeping.folder
    filename = housekeeping.client + '_Scheme.xls'
    schemetable.save_scheme(folder, filename)

def get_se_row():
    row = schemetable.currentRow()
    if row == -1:
        log.warn('No row selected')
        return
    log.info('Row ' + str(row + 1) + ' selected for weighing')

    se_row_data = schemetable.get_se_row_dict(row)

    return se_row_data

def collect_n_good_runs():
    try:
        housekeeping.cfg.bal_class
    except:
        housekeeping.initialise_cfg()

    info = housekeeping.info

    se_row_data = get_se_row()

    weigh_thread = WeighingThread()
    all_my_threads.append(weigh_thread)
    good_runs = weigh_thread.show(se_row_data, info)
    print(good_runs, 'in main gui')


def reanalyse_weighings():
    se_row_data = get_se_row()
    filename = housekeeping.client+'_'+se_row_data['nominal']
    analyse_all_weighings_in_file(housekeeping.folder, filename, se_row_data['scheme_entry'],
                                  timed=housekeeping.timed, drift=housekeeping.drift)
    if housekeeping.drift:
        log.info('Weighing re-analysed using ' + housekeeping.drift + ' correction')
    else:
        log.info('Weighing re-analysed using optimal drift correction')

def display_se_results():
    pass

def display_collated():
    try:
        folder = housekeeping.folder
        client = housekeeping.client
        client_wt_IDs = housekeeping.client_masses
        check_wt_IDs = housekeeping.cfg.all_checks['weight ID']
        std_masses = housekeeping.cfg.all_stds
    except:
        housekeeping.initialise_cfg()

    data = collate_all_weighings(schemetable, housekeeping)

    fmc_info = {'url': housekeeping.folder + "\\" + housekeeping.client + '_finalmasscalc.json',
                'Client': housekeeping.client,
                'client_wt_IDs': housekeeping.client_masses,
                'check_wt_IDs': housekeeping.cfg.all_checks['weight ID'],
                'std_masses': housekeeping.cfg.all_stds,
                'nbc': True,
                'corr': housekeeping.correlations,
    }
    mass_thread.show(data, fmc_info)


all_my_threads = []

sys.excepthook = excepthook

# could ask user to load config file here?

gui = application()

mass_thread = MassCalcThread()

w = QtWidgets.QWidget()
rect = QtWidgets.QDesktopWidget()
w.setFixedSize(rect.width()*0.9, rect.height()*0.45)
w.setWindowTitle('Mass Calibration: Main Window')

housekeeping = Housekeeping()
lhs_panel_group = housekeeping.lhs_panel_group()
schemetable = SchemeTable()
central_panel_group = make_table_panel()

layout = QtWidgets.QHBoxLayout()
layout.addWidget(lhs_panel_group, 3)
layout.addWidget(central_panel_group, 4)
layout.addWidget(Logger(fmt='%(message)s'), 4)
w.setLayout(layout)

w.show()
gui.exec()


def clean_up_thread(self, thread_instance):
    for i, item in enumerate(all_my_threads):
        if thread_instance is item:
            del all_my_threads[i]
            break