from src.results_summary import WordDoc
import os
from msl.io import read, read_table_excel



def export_results_summary(job, client, folder, client_wt_IDs, checks, stds):
    wd = WordDoc()
    wd.init_report(job, client, folder)

    scheme_file = os.path.join(folder, client + '_Scheme.xls')
    scheme = read_table_excel(scheme_file)
    print(stds, stds['weight IDs'], stds['path'])
    print(checks, checks['weight IDs'], checks['path'])
    wd.add_weighing_scheme(scheme, client_wt_IDs, check_wt_IDs, check_set_file_path, std_wt_IDs, std_set_file_path)

    finalmasscalc_file = os.path.join(folder, client+'_finalmasscalc.json')
    fmc_root = read(finalmasscalc_file)
    wd.add_mls(fmc_root)

    wd.add_weighing_datasets()

    wd.make_normal_text("This is a sentence of normal text.")
    wd.make_normal_text("This is another sentence of normal text")

    wd.save_doc(r'I:\MSL\Private\Mass\transfer\Balance Software\Sample Data\testWordFile.docx')

    wd.close_doc()

def checkable_summary(housekeeping, schemetable):

    print("Summary of Calibration " + housekeeping.client)
    print("Data saved in " + housekeeping.folder)
    print()
    print("Weighing Scheme")
    print("Weight Groups \tNominal (g) \tBalance \t#runs collected")
    for row in range(schemetable.rowCount()):
        try:
            print(schemetable.cellWidget(row, 0).text() + "\t" +
                  schemetable.cellWidget(row, 1).text() + "\t" +
                  schemetable.cellWidget(row, 2).currentText() + "\t" +
                  schemetable.cellWidget(row, 3).text())
        except AttributeError:
            pass
    print()
    print("Client weights: " + housekeeping.client_masses)
    print("Check weights: " + str(housekeeping.cfg.all_checks))
    if housekeeping.cfg.all_checks is not None:
        print("Check set file: " + housekeeping.cfg.all_checks['Set file'])
    print("Standard weights: " + str(housekeeping.cfg.all_stds))
    print("Standard set file: " + housekeeping.cfg.all_stds['Set file'])



if __name__ == '__main__':
    folder = r'I:\MSL\Private\Mass\transfer\Balance Software\Sample Data\UMX5'
    job = 'UMX5'
    client = 'ppe_check'
    client_wt_IDs = "boo"
    check_wt_IDs = "boo hoo"
    check_set_file_path = "boo hoo hoo"
    std_wt_IDs = "boo hoo hoo hoo hoo"
    std_set_file_path = "boo hoo ha"

    export_results_summary(job, client, folder, client_wt_IDs, check_wt_IDs, check_set_file_path, std_wt_IDs, std_set_file_path)