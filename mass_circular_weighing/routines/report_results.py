import os

from msl.io import read, read_table_excel

from ..log import log
from ..results_summary import WordDoc


def export_results_summary(cfg, check_file, std_file, incl_datasets):

    wd = WordDoc()
    wd.init_report(cfg.job, cfg.client, cfg.folder,)

    if os.path.isfile(os.path.join(cfg.folder, cfg.client + '_Scheme.xls')):
        scheme_path = os.path.join(cfg.folder, cfg.client + '_Scheme.xls')
        scheme = read_table_excel(scheme_path)
    elif os.path.isfile(os.path.join(cfg.folder, cfg.client + '_Scheme.xlsx')):
        scheme_path = os.path.join(cfg.folder, cfg.client + '_Scheme.xlsx')
        scheme = read_table_excel(scheme_path)
    else:
        log.error('Please save scheme and then continue')
        return None

    finalmasscalc_file = os.path.join(cfg.folder, cfg.client +'_finalmasscalc.json')
    fmc_root = read(finalmasscalc_file)

    wd.add_weighing_scheme(scheme, fmc_root, check_file, std_file)
    wd.add_mls(fmc_root, cfg.folder, cfg.client)

    wd.add_weighing_datasets(cfg.client, cfg.folder, scheme, incl_datasets)

    save_file = os.path.join(cfg.folder, cfg.client + '_Summary.docx')
    wd.save_doc(save_file)

    wd.close_doc()
