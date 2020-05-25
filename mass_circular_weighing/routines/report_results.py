import os
import numpy as np

from msl.io import read, read_table_excel

from ..log import log
from ..results_summary import WordDoc
from ..results_summary_LaTeX import LaTexDoc


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
    if os.path.isfile(os.path.join(cfg.folder, cfg.client + '_Scheme.xls')):
        scheme_path = os.path.join(cfg.folder, cfg.client + '_Scheme.xls')
        scheme = read_table_excel(scheme_path)
    elif os.path.isfile(os.path.join(cfg.folder, cfg.client + '_Scheme.xlsx')):
        scheme_path = os.path.join(cfg.folder, cfg.client + '_Scheme.xlsx')
        scheme = read_table_excel(scheme_path)
    else:
        log.error('Please save scheme and then continue')
        return None

    # get balance model numbers instead of balance aliases
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
    ld.add_mls(fmc_root)
    ld.add_weighing_datasets(cfg.client, cfg.folder, scheme, cfg, incl_datasets)
    ld.close_doc()
    log.info("LaTeX file saved to {}".format(latex_file))

    # Make Word Output file
    wd = WordDoc()
    wd.init_report(cfg.job, cfg.client, cfg.folder,)
    wd.add_weighing_scheme(mod_scheme, fmc_root, check_file, std_file)
    wd.add_mls(fmc_root, cfg.folder, cfg.client)
    wd.add_weighing_datasets(cfg.client, cfg.folder, scheme, incl_datasets)
    save_file = os.path.join(cfg.folder, cfg.client + '_Summary.docx')
    wd.save_doc(save_file)
    wd.close_doc()
    log.info("Word file saved to {}".format(save_file))

    log.info("File export complete")


