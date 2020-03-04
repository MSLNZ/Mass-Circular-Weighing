from src.results_summary import WordDoc
import os
from msl.io import read, read_table_excel


def export_results_summary(cfg, check_file, std_file, incl_datasets):

    wd = WordDoc()
    wd.init_report(cfg.job, cfg.client, cfg.folder,)

    scheme_file = os.path.join(cfg.folder, cfg.client + '_Scheme.xls')
    scheme = read_table_excel(scheme_file)

    finalmasscalc_file = os.path.join(cfg.folder, cfg.client +'_finalmasscalc.json')
    fmc_root = read(finalmasscalc_file)

    wd.add_weighing_scheme(scheme, fmc_root, check_file, std_file)
    wd.add_mls(fmc_root, cfg.folder, cfg.client)

    wd.add_weighing_datasets(cfg.client, cfg.folder, scheme, incl_datasets)

    save_file = os.path.join(cfg.folder, cfg.client + '_Summary.docx')
    wd.save_doc(save_file)

    wd.close_doc()
