"""
Prepares an easily-checked summarised form of the raw and processed data
"""
import os
import numpy as np

from msl.io import read, read_table_excel

from ..log import log
# from ..results_summary import WordDoc
from ..results_summary_LaTeX import LaTexDoc
from ..results_summary_Excel import ExcelSummaryWorkbook


def export_results_summary(cfg, check_file, std_file, incl_datasets):
    """Export results summaries to Word, Excel and LaTeX

    Parameters
    ----------
    cfg : Config object
        Configuration from config.xml file
    check_file : path or None
        path to reference mass set file for checks, if used
    std_file : path
        path to reference mass set file for standards
    incl_datasets : set
        set of included datasets as (nominal mass, scheme entry, run)

    Returns
    -------
    Saved output files in the save folder specified in cfg.
    Excel data contains mass differences and final mass values.
    Word and LaTeX docs contain tables of all relevant data, along with tables of metadata.
    """

    # gather relevant files
    if os.path.isfile(os.path.join(cfg.folder, cfg.client + '_Scheme.xlsx')):
        scheme_path = os.path.join(cfg.folder, cfg.client + '_Scheme.xlsx')
        scheme = read_table_excel(scheme_path)
    elif os.path.isfile(os.path.join(cfg.folder, cfg.client + '_Scheme.xls')):
        scheme_path = os.path.join(cfg.folder, cfg.client + '_Scheme.xls')
        scheme = read_table_excel(scheme_path)
        log.warning("Tell Rebecca to fix this")
    else:
        log.error('Please save scheme and then continue')
        return None

    # get balance model numbers instead of balance aliases
    if len(scheme.shape) == 1:    # catch for if only one entry in scheme
        mod_scheme = np.ndarray((1, 4), dtype=type(scheme.data))
        mod_scheme[0][0] = ' - '.join(scheme.data[0].split())
        mod_scheme[0][1] = scheme.data[1]
        mod_scheme[0][2] = cfg.equipment[scheme.data[2]].model
        mod_scheme[0][3] = scheme.data[3]
    else:
        mod_scheme = np.ndarray(np.shape(scheme.data), dtype=type(scheme.data))
        for row in range(len(mod_scheme)):
            mod_scheme[row][0] = ' - '.join(scheme.data[row][0].split())
            mod_scheme[row][1] = scheme.data[row][1]
            mod_scheme[row][2] = cfg.equipment[scheme.data[row][2]].model
            mod_scheme[row][3] = scheme.data[row][3]

    finalmasscalc_file = os.path.join(cfg.folder, cfg.client +'_finalmasscalc.json')
    fmc_root = read(finalmasscalc_file)

    # Make LaTeX Output file
    latex_file = os.path.join(cfg.folder, cfg.client + '_Summary.tex')
    ld = LaTexDoc(latex_file)
    ld.init_report(cfg.job, cfg.client, cfg.folder)
    ld.add_weighing_scheme(mod_scheme, fmc_root, check_file, std_file, )
    ld.add_mls(fmc_root, cfg.folder, cfg.client)
    ld.add_weighing_datasets(cfg.client, cfg.folder, scheme, cfg, incl_datasets)
    ld.close_doc()
    log.info("LaTeX file saved to {}".format(latex_file))

    # make Excel summary file
    xl_output_file = os.path.join(cfg.folder, cfg.client + '_Summary.xlsx')
    xl = ExcelSummaryWorkbook()
    xl.load_scheme_file(scheme_path, fmc_root, check_file, std_file, cfg.job, cfg.client, cfg.folder)
    xl.add_mls(fmc_root)
    xl.add_all_cwdata(cfg, incl_datasets)
    xl.add_overall_ambient()
    xl.save_workbook(xl_output_file)

    # Make Word Output file - not in use at present
    # wd = WordDoc()
    # wd.init_report(cfg.job, cfg.client, cfg.folder,)
    # wd.add_weighing_scheme(mod_scheme, fmc_root, check_file, std_file)
    # wd.add_mls(fmc_root, cfg.folder, cfg.client)
    # wd.add_weighing_datasets(cfg.client, cfg.folder, scheme, incl_datasets, cfg)
    # save_file = os.path.join(cfg.folder, cfg.client + '_Summary.docx')
    # wd.save_doc(save_file)
    # wd.close_doc()
    # log.info("Word file saved to {}".format(save_file))

    log.info("File export complete")


