"""
Results summary in LaTeX format
Called from routines.report_results.py
"""
import os
import xlwt
from tabulate import tabulate

from msl.io import read

from ..constants import IN_DEGREES_C, MU_STR
from ..log import log


def greg_format(number):
    try:
        before, after = '{:.9f}'.format(number).split('.')
        return before + '.' + ' '.join(after[i:i+3] for i in range(0, len(after), 3))
    except ValueError as e:
        log.error("Couldn't put {} in Greg format. {}".format(number, e))
        return str(number)


def list_to_csstr(idlst):
    idstr = ""
    for id in idlst:
        idstr += id + ", "
    return idstr.strip(" ").strip(",")


def save_mls_excel(data, folder, client, sheet_name):
    header = data.metadata.get('metadata')['headers']
    path = os.path.join(folder, client + '_' + sheet_name + '.xls')
    workbook = xlwt.Workbook()
    sheet = workbook.add_sheet(sheet_name)

    for j, text in enumerate(header):
        sheet.write(0, j, text)

    for row in range(len(data)):
        for col in range(len(data[row])):
            sheet.write(row + 1, col, data[row][col])

    workbook.save(path)
    log.info('Data saved to {} in {}'.format(sheet_name, path))


class LaTexDoc(object):
    def make_title(self, title):
        self.fp.write(
            '\\begin{document}\n'
            '\\title{' + title.replace('_', " ") + '}\n'
            '\\maketitle\n\n'
        )

    def __init__(self, filename):
        #
        self.fp = open(filename, mode='w', encoding='utf-8')
        self.fp.write(
                '\\documentclass[12pt]{article}\n'
                '\\usepackage[a4paper,margin=2cm]{geometry}\n'
                "\\usepackage{lscape}\n"
                '\\usepackage{booktabs}\n'
                '\\usepackage{tabu}\n'
                '\\usepackage{longtable}\n'
                "\\usepackage{siunitx}\n"
                '\\usepackage{url}\n'
                '\\usepackage{layouts}\n\n'
        )

        self.collate_ambient = {'T'+IN_DEGREES_C: [], 'RH (%)': []}

    def make_heading1(self, heading):
        # Insert a heading.
        self.fp.write('\n\\section*{' + heading + '}\n')

    def make_heading2(self, heading):
        # Insert a heading.
        self.fp.write('\n\\subsection*{' + heading + '}\n')

    def make_heading3(self, heading):
        # Insert a heading.
        self.fp.write('\n\\subsubsection*{' + heading + '}\n')

    def make_heading4(self, heading):
        # Insert a heading.
        self.fp.write('\n\\paragraph{\\emph{' + heading + '}}\n')

    def make_normal_text(self, text, size=None):
        #Insert another paragraph.
        if size:
            self.fp.write('\n\\paragraph{\\' + size + '{' + text + '}}\n')
        else:
            self.fp.write('\n\\paragraph{' + text + '}\n')

    def page_break(self):
        self.fp.write('\\pagebreak')

    def close_doc(self):
        self.fp.write(
                '\n'
                '\\end{document}'
            )
        self.fp.close()

    def init_report(self, job, client, operator, folder):
        self.make_title(job + " for " + client)
        self.fp.write(f"Operator: {operator} \\\\ \n")
        self.fp.write("Data files saved in \\url{" + folder + '} \n')

    def make_table_wts(self, client_wt_IDs, check_wt_IDs, check_set_file_path, std_wt_IDs, std_set_file_path):
        self.fp.write(
            '\n\\begin{tabu}{lX}\n'
            ' Client weights:  & '+ str(client_wt_IDs) + '\\\\ \n'
            ' Check weights:   & '+ str(check_wt_IDs) + '\\\\ \n'
            '                  & \\url{'+ str(check_set_file_path) + '} \\\\ \n'
            ' Standard weights & '+ str(std_wt_IDs) + '\\\\ \n'
            '                  & \\url{'+ str(std_set_file_path) + '} \\\\ \n'
            '\n\\end{tabu} \n'
        )

    def make_table_wts_nochecks(self, client_wt_IDs, std_wt_IDs, std_set_file_path):
        self.fp.write(
            '\n\\begin{tabu}{lX}\n'
            ' Client weights:  & ' + str(client_wt_IDs) + '\\\\ \n'
            ' Check weights:   &    None                    \\\\ \n'
            ' Standard weights & '+ str(std_wt_IDs) + '\\\\ \n'
            '                  & \\url{'+ str(std_set_file_path) + '} \\\\ \n'
            '\n\\end{tabu} \n'
        )

    def make_table_massdata(self, data, headers, masscol=None):
        """Makes table of structured data containing one column of mass data to be formatted in 'Greg' formatting"""
        if masscol == 2:  # Input data table
            col_type_str = "ll S[round-mode=places,round-precision=9] S S"
            headerstr = " {+ weight group} & {- weight group} & {mass difference (g)} & " \
                        "{balance uncertainty ($\\mu$g)} & {residual ($\\mu$g)} \\\\"
        elif masscol == 3:  # MSL data table
            col_type_str = "S ll S[round-mode=places,round-precision=9] S S S l"
            headerstr = " {Nominal (g)} & {Weight ID} & {Set ID} & {Mass value (g)} & {Uncertainty ($\\mu$g)} & " \
                        "{95\% CI} & {Cov} & {c.f. Reference value (g)} \\\\"
        else:
            log.error("Unknown data table type")
            return None

        self.fp.write(
            "\n\\begin{small}\n"
            "\\begin{longtabu} to \\textwidth {" + col_type_str + "}\n"
            "\\toprule"
        )
        self.fp.write(headerstr)
        self.fp.write("\n\\midrule")

        data_as_str = "\n"
        for row in data:
            for e, entry in enumerate(row):
                if e == masscol:
                    data_as_str += greg_format(entry) + " & "
                else:
                    data_as_str += str(entry) + " & "
            data_as_str = data_as_str.strip('& ') + '\\\\ \n'
        data_as_str = data_as_str.replace("Δ", "\t$\\Delta$").replace('+', ' + ').replace('None', " ")
        self.fp.write(data_as_str)

        self.fp.write(
            "\n\\bottomrule"
            "\n\\end{longtabu}"
            "\n\\end{small}\n"
        )

    def add_weighing_scheme(self, scheme, fmc_root, check_file, std_file):
        client_wt_IDs = list_to_csstr(fmc_root["1: Mass Sets"]["Client"].metadata.get("Weight ID"))
        if check_file:
            checks = {
                'Weight ID': list_to_csstr(fmc_root["1: Mass Sets"]["Check"].metadata.get("Weight ID")),
                'Set file': check_file
            }
        else:
            checks = None
        std_wts = list_to_csstr(fmc_root["1: Mass Sets"]["Standard"].metadata.get("Weight ID"))

        self.fp.write("\\begin{landscape}\n")
        self.make_heading1('Weighing Scheme')
        headers = ['Weight groups', 'Nominal mass(g)', 'Balance', '# runs']
        self.fp.write(tabulate(scheme, headers=headers, tablefmt="latex_booktabs"))

        self.make_normal_text("")

        if checks is not None:
            self.make_table_wts(client_wt_IDs, checks['Weight ID'], checks['Set file'], std_wts, std_file)
        else:
            self.make_table_wts_nochecks(client_wt_IDs, std_wts, std_file)
        self.fp.write("\\end{landscape}\n")

    def add_mls(self, fmc_root, folder, client):
        """Adds matrix least squares section to summary file"""
        self.fp.write("\\begin{landscape}\n")
        self.make_heading1('Matrix Least Squares Analysis')
        timestamp = fmc_root['metadata'].metadata['Timestamp'].split()
        self.make_normal_text('Date: ' + timestamp[0] + '\tTime: ' + timestamp[1])

        self.make_heading2('Input data')
        input_data = fmc_root['2: Matrix Least Squares Analysis']["Input data with least squares residuals"]
        h1 = input_data.metadata.get('metadata')['headers']
        self.make_table_massdata(input_data, h1, 2)
        # save_mls_excel(input_data, folder, client, sheet_name="Differences")

        self.make_heading2('Mass values from Least Squares solution')
        mvals = fmc_root['2: Matrix Least Squares Analysis']["Mass values from least squares solution"]
        h2 = mvals.metadata.get('metadata')['headers']
        self.make_table_massdata(mvals, h2, 3)
        # save_mls_excel(mvals, folder, client, sheet_name="Mass_Values")
        meta = fmc_root['2: Matrix Least Squares Analysis']['metadata'].metadata
        self.make_normal_text(
                "Number of observations = " + str(meta['Number of observations']) +
                ", Number of unknowns = " + str(meta['Number of unknowns']) +
                ", Degrees of freedom = " + str(meta['Degrees of freedom'])
        )
        self.make_normal_text(
                "Relative uncertainty for no buoyancy correction (ppm) = " +
                str(meta['Relative uncertainty for no buoyancy correction (ppm)'])
        )
        self.make_normal_text(
            "Sum of residues squared ($\\mu g^2$) = " + str(meta['Sum of residues squared ('+MU_STR+'g^2)'])
        )
        self.fp.write("\\end{landscape}\n")

    def make_table_run_meta(self, cw_run_meta, bal_model):
        """Makes table of ambient and other metadata from circular weighing run"""

        try:
            self.fp.write(
                '\\begin{tabular}{llllllll}\n'
                ' Time:  & '+ cw_run_meta.get("Mmt Timestamp").split()[1] + '&'
                ' Date:   & '+ cw_run_meta.get("Mmt Timestamp").split()[0]+ '&'
                ' Balance  & '+ bal_model + '&'
                ' Unit: & ' + cw_run_meta.get("Unit") + '\\\\ \n'
                ' Temp (°C): & ' + cw_run_meta.get("T"+IN_DEGREES_C) + '&'
                ' RH (\\%): & ' + cw_run_meta.get("RH (%)") + '&' 
                " Ambient OK? & " + str(cw_run_meta.get("Ambient OK?")) + '\\\\ \n'     
                '\\end{tabular} \n'
            )
        except TypeError:  # e.g if ambient condition data is missing
            self.fp.write(
                '\\begin{tabular}{llllllll}\n'
                ' Time:  & '+ cw_run_meta.get("Mmt Timestamp").split()[1] + '&'
                ' Date:   & '+ cw_run_meta.get("Mmt Timestamp").split()[0]+ '&'
                ' Balance  & '+ bal_model + '&'
                ' Unit: & ' + cw_run_meta.get("Unit") + '\\\\ \n'
                ' Temp (°C): & ' + "None available" + '&'
                ' RH (\\%): & ' + "None available" + '&' 
                " Ambient OK? & " + "None available" + '\\\\ \n'     
                '\\end{tabular} \n'
            )



    def make_table_diffs_meta(self, cw_anal_meta):
        '''Makes table of metadata from circular weighing analysis'''
        res_dict = cw_anal_meta.get("Residual std devs")
        drifts = ""
        try:
            drifts += 'linear drift:\t' + cw_anal_meta.get("linear drift")
            drifts += '\nquadratic drift:\t' + cw_anal_meta.get("quadratic drift")
            drifts += '\ncubic drift:\t' + cw_anal_meta.get("cubic drift")
        except TypeError:
            pass
        self.fp.write(
            '\n\\begin{small}'
            '\n\\begin{tabu}{lX}\n'
            ' Analysis uses times?  & '+ str(cw_anal_meta.get("Uses mmt times")) + '\\\\ \n'
            ' Residual std devs:  & '+ res_dict.strip("{").strip("}") + '\\\\ \n'
            ' Selected drift:  & ' + cw_anal_meta.get("Selected drift") + '\\\\ \n'
            ' Drift components (' + cw_anal_meta.get("Drift unit") + "): & " + drifts + '\\\\ \n'
            '\\end{tabu} \n'
            '\\end{small} \n'
        )

    def make_table_cwdata(self, wtpos, weighdata):
        '''Makes table of raw circular weighing data with headings '(position) weight group',
        and data as twin columns of times and balance readings

        Parameters
        ----------
        wtpos : list of weight groups and positions as tuples
        weighdata : structured array
        '''
        rows = len(weighdata)
        cols = len(wtpos) * 2
        col_str = cols*'S'

        self.fp.write(
            '\n\\begin{tabular}{'+col_str+'}'
            '\n\\toprule \n'
        )

        headers = ""
        time_reads = ""
        for c in range(len(wtpos)):
            headers += " \\multicolumn{2}{c}{(" + str(wtpos[c][1]) + ") " + str(wtpos[c][0]) + '} & '
            time_reads += ' {Time} & {Reading} & '

        self.fp.write(headers.strip('& ')+'\\\\ \n')
        self.fp.write(time_reads.strip('& ')+'\\\\ \n')
        self.fp.write(' \\midrule \n')

        for r in range(0, rows):
            row_str = " "
            for c in range(len(wtpos)):
                row_str += '{:.2f}'.format(weighdata[r][c][0]) + ' & ' + str(weighdata[r][c][1]) + ' & '
            self.fp.write(row_str.strip('& ') + '\\\\ \n')

        self.fp.write(
            '\\bottomrule \n'
            '\\end{tabular}\n'
        )

    def make_table_cw_diffs(self, data):
        """Makes table of differences e.g. position 0 - position 1, mass difference, residual.
        Uses original units from weighing."""
        headers = "{+ weight group} & {- weight group} & {mass difference} & {residual} \\\\"
        self.fp.write(
            '\n\\begin{tabular}{l l S S}'
            '\n\\toprule'
            '\n'+headers+
            '\n\\midrule'
        )
        for i in range(len(data)):
            row_str = "\n" + data["+ weight group"][i] + " & " + \
                  data["- weight group"][i]+" & "+ \
                  greg_format(data["mass difference"][i])+" & "+ \
                  greg_format(data["residual"][i]) + " \\\\"
            self.fp.write(row_str)
        self.fp.write(
            '\n\\bottomrule'
            '\n\\end{tabular}'
            '\n'
        )

    def make_table_collated_diffs(self, data):
        """Makes table of differences e.g. position 0 - position 1, mass difference, residual.
        Uses g for all mass values."""
        headers = "{+ weight group} & {- weight group} & {mass difference (g)} & {residual (g)} \\\\"
        self.fp.write(
            '\n\\begin{tabular}{l l S S}'
            '\n\\toprule'
            '\n' + headers +
            '\n\\midrule'
        )
        for i in range(len(data)):
            row_str = "\n" + data["+ weight group"][i] + " & " + \
                      data["- weight group"][i] + " & " + \
                      greg_format(data["mass difference (g)"][i]) + " & " + \
                      greg_format(data['residual (' + MU_STR + 'g)'][i] * 1e-6) + " \\\\"
            self.fp.write(row_str)
        self.fp.write(
            '\n\\bottomrule'
            '\n\\end{tabular}'
            '\n'
        )

    def add_collated_data(self, cw_file, se):
        """Adds the collated data calculated for an automatic weighing, if relevant.

        Parameters
        ----------
        cw_file : path
        se : str
        """
        if not os.path.isfile(cw_file):
            log.warning(f'No data yet collected for {se}')
        else:
            log.debug(f'Reading {cw_file}')
            root = read(cw_file)

            try:
                root['Circular Weighings'][se]
            except KeyError:
                log.warning(f'No data yet collected for {se}')
                return

            for dataset in root['Circular Weighings'][se].datasets():
                if dataset.name[-8:] == "Collated":
                    self.make_heading3("Collated data")
                    self.make_table_collated_diffs(dataset)
                    self.fp.write(
                        '\n\\begin{small}'
                        '\n\\begin{tabu}{lX}'
                    )
                    for key, value in dataset.metadata.items():
                        self.fp.write("\n " + key + " & " + str(value) + ' \\\\')
                    self.fp.write(
                        '\n\\end{tabu}'
                        '\n\\end{small}'
                        '\n'
                    )

    def add_weighing_dataset(self, cw_file, se, nom, incl_datasets, cfg):
        """How to add all datasets from each circular weighing for a given scheme entry

        Parameters
        ----------
        cw_file : path
        se : str
        nom : str
        incl_datasets : set
        cfg : configuration instance
        """
        if not os.path.isfile(cw_file):
            log.warning(f'No data yet collected for {se}')
        else:
            self.make_heading2(se)
            wt_grps = se.split()

            log.debug(f'Reading {cw_file}')
            root = read(cw_file)

            try:
                root['Circular Weighings'][se]
            except KeyError:
                log.warning(f'No data yet collected for {se}')
                return

            for dataset in root['Circular Weighings'][se].datasets():
                dname = dataset.name.split('_')

                if dname[0][-8:] == 'analysis':
                    run_id = 'run_' + dname[2]

                    weighdata = root.require_dataset(
                        root['Circular Weighings'][se].name + '/measurement_' + run_id)

                    if (str(float(nom)), se, dname[2]) in incl_datasets:
                        self.make_heading3(run_id.replace('_', ' '))

                        try:
                            temps = weighdata.metadata.get("T" + IN_DEGREES_C).split(" to ")
                            for t in temps:
                                self.collate_ambient['T' + IN_DEGREES_C].append(float(t))
                            rhs = weighdata.metadata.get("RH (%)").split(" to ")
                            for rh in rhs:
                                self.collate_ambient['RH (%)'].append(float(rh))
                        except AttributeError:
                            log.warning(f"Missing ambient conditions for {se} {run_id}")

                    else:
                        self.make_heading3(run_id.replace('_', ' ') + " (EXCLUDED)")

                    # Get balance model number from balance alias:
                    bal_alias = weighdata.metadata.get("Balance")
                    bal_model = cfg.equipment[bal_alias].model
                    self.make_table_run_meta(weighdata.metadata, bal_model)

                    self.make_heading4('Balance readings \\\\')
                    self.fp.write('Note times are in minutes; weighing positions are in brackets.  \\\\ \n')

                    wtpos = []
                    try:                # new way of recording groups
                        d = weighdata.metadata.get("Weight group loading order")
                        for key, value in d.items():
                            wtpos.append([value, key.strip("Position ")])
                    except KeyError:    # old way of recording groups
                        for i in range(1, len(wt_grps) + 1):
                            a = weighdata.metadata.get("grp"+str(i))
                            wtpos.append([a, i])
                    self.make_table_cwdata(wtpos, weighdata)

                    self.make_heading4('Column average differences  \\\\ \n')
                    self.fp.write(' ')
                    analysisdata = root.require_dataset(
                        root['Circular Weighings'][se].name + '/analysis_' + run_id)

                    self.make_table_cw_diffs(analysisdata)
                    self.fp.write("\n   ") # make_normal_text(" ", 'tiny')
                    self.make_table_diffs_meta(analysisdata.metadata)

    def add_weighing_datasets(self, client, folder, scheme, cfg, incl_datasets, ):
        self.make_heading1("Circular Weighing Data")
        for row in scheme:
            se = row[0]
            nom = row[1]
            cw_file = os.path.join(folder, f'{client}_{nom}.json')
            if not os.path.isfile(cw_file):
                log.warning(f'No data yet collected for {se}')
            else:
                self.add_weighing_dataset(cw_file, se, nom, incl_datasets, cfg)
                self.add_collated_data(cw_file, se)

        self.make_heading2("Overall ambient conditions for included weighings")
        if self.collate_ambient["T" + IN_DEGREES_C]:
            self.fp.write(
                "T"+IN_DEGREES_C+":\t" + str(min(self.collate_ambient["T"+IN_DEGREES_C])) + " to " + str(max(self.collate_ambient["T"+IN_DEGREES_C])) + "\\\\"
            )
        else:
            self.fp.write("No temperature data collated. \\\\")

        if self.collate_ambient["RH (%)"]:
            self.fp.write(
                "RH (\\%):\t" + str(round(min(self.collate_ambient["RH (%)"]), 1)) + " to " + str(round(max(self.collate_ambient["RH (%)"]), 1))
            )
        else:
            self.fp.write("No humidity data collated. \\\\")




