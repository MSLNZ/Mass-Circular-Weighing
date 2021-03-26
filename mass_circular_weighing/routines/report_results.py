"""
Prepares an easily-checked summarised form of the raw and processed data
"""
import os
import numpy as np

from msl.io import read, read_table_excel

from ..log import log
# from ..routine_classes.results_summary_Word import WordDoc
from ..routine_classes.results_summary_LaTeX import LaTexDoc
from ..routine_classes.results_summary_Excel import ExcelSummaryWorkbook


def export_results_summary(cfg, check_file, std_file, incl_datasets):
    """Export results summaries to LaTeX and Excel

    Parameters
    ----------
    cfg : Config object
        Configuration class instance created using Admin.xlsx and config.xml files
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
    # load scheme in cfg object
    headers, scheme = cfg.load_scheme()
    # note that scheme is returned as a list of lists here

    # get balance model numbers instead of balance aliases
    mod_scheme = np.ndarray(np.shape(scheme), dtype=object)
    for row in range(len(mod_scheme)):
        mod_scheme[row][0] = ' - '.join(scheme[row][0].split())
        mod_scheme[row][1] = float(scheme[row][1])
        mod_scheme[row][2] = cfg.equipment[scheme[row][2]].model
        mod_scheme[row][3] = int(scheme[row][3])

    finalmasscalc_file = os.path.join(cfg.folder, cfg.client +'_finalmasscalc.json')
    fmc_root = read(finalmasscalc_file)

    # Make LaTeX Output file
    latex_file = os.path.join(cfg.folder, cfg.client + '_Summary.tex')
    ld = LaTexDoc(latex_file)
    ld.init_report(cfg.job, cfg.client, cfg.operator, cfg.folder)
    ld.add_weighing_scheme(mod_scheme, fmc_root, check_file, std_file, )
    ld.add_mls(fmc_root, cfg.folder, cfg.client)
    ld.add_weighing_datasets(cfg.client, cfg.folder, scheme, cfg, incl_datasets)
    ld.close_doc()
    log.info("LaTeX file saved to {}".format(latex_file))

    # make Excel summary file
    xl_output_file = os.path.join(cfg.folder, cfg.client + '_Summary.xlsx')
    xl = ExcelSummaryWorkbook(cfg)
    xl.format_scheme_file()
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


