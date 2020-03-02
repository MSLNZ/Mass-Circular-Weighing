from msl.loadlib import LoadLibrary #, utils
import os
from msl.io import read
import xlwt
from src.constants import IN_DEGREES_C, MU_STR
import src.cv as cv
from src.log import log
# info = utils.get_com_info()
# for key, value in info.items():
#     if 'Microsoft' in value['ProgID']:
#         print(key, value)

# https://docs.microsoft.com/en-us/office/vba/api/word.application
# https://support.microsoft.com/en-nz/help/316383/how-to-automate-word-from-visual-basic-net-to-create-a-new-document

def greg_format(number):
    before, after = '{:.9f}'.format(number).split('.')
    return before + '.' + ' '.join(after[i:i+3] for i in range(0, len(after), 3))


def list_to_csstr(idlst):
    idstr = ""
    for id in idlst:
        idstr += id + ", "
    return idstr.strip(" ").strip(",")


def save_mls_excel(data):
    header = data.metadata.get('metadata')['headers']

    path = os.path.join(cv.folder.get(), cv.client.get()+'_AllDiffs.xls')
    workbook = xlwt.Workbook()
    sheet = workbook.add_sheet('Differences')

    for j, text in enumerate(header):
        sheet.write(0, j, text)

    for row in range(len(data)):
        for col in range(len(data[row])):
            sheet.write(row + 1, col, data[row][col])

    workbook.save(path)
    log.info('Collated differences saved to ' + str(path))


class WordDoc(object):
    def __init__(self):
        # Start Word and open the document template.
        self.oWord  = LoadLibrary('Word.Application', 'com').lib
        self.oWord.Visible = True
        self.oDoc = self.oWord.Documents.Add()

        self.smallfont = 9  # sets size of text in data tables

        self.collate_ambient = {'T'+IN_DEGREES_C: [], 'RH (%)': []}

    def make_title(self, text):
        oPara = self.oDoc.Content.Paragraphs.Add()
        oPara.Range.Text = text
        # oPara0.Range.Font.Bold = True
        oPara.Style = -63 # wdStyleTitle
        oPara.Format.SpaceAfter = 12    # 12 pt spacing after title.
        oPara.Range.InsertParagraphAfter()

    def make_heading1(self, heading):
        # Insert a heading.
        oPara = self.oDoc.Content.Paragraphs.Add()
        oPara.Range.Text = heading
        oPara.Style = -2
        oPara.Range.InsertParagraphAfter()

    def make_heading2(self, heading):
        # Insert a heading.
        oPara = self.oDoc.Content.Paragraphs.Add()
        oPara.Range.Text = heading
        oPara.Style = -3
        oPara.Range.InsertParagraphAfter()

    def make_heading3(self, heading):
        # Insert a heading.
        oPara = self.oDoc.Content.Paragraphs.Add()
        oPara.Range.Text = heading
        oPara.Style = -4
        oPara.Range.InsertParagraphAfter()

    def make_heading4(self, heading):
        # Insert a heading.
        oPara = self.oDoc.Content.Paragraphs.Add()
        oPara.Range.Text = heading
        oPara.Style = -5
        oPara.Range.InsertParagraphAfter()

    def make_normal_text(self, text, size=None):
        #Insert another paragraph.
        oPara2t = self.oDoc.Content.Paragraphs.Add()
        oPara2t.Range.Text = text
        if size:
            oPara2t.Range.Font.Size = size
        oPara2t.Format.SpaceAfter = 0   # 0 pt spacing after paragraph.
        oPara2t.Range.InsertParagraphAfter()

    def page_break(self):
        oRng = self.oDoc.Range()
        oRng.Collapse(0)  # Word.WdCollapseDirection.wdCollapseEnd
        oRng.InsertBreak(7)  # Word.WdBreakType.wdPageBreak
        oRng.Collapse(0)  # Word.WdCollapseDirection.wdCollapseEnd

    def save_doc(self, filename):
        self.oDoc.SaveAs(filename)

    def close_doc(self):
        self.oWord.Quit()

    def init_report(self, job, client, folder):
        self.make_title(job + " for " + client)
        self.make_normal_text("Data files saved in " + folder)

    def make_table_norm(self, data):
        # 'Insert a table, fill it with data, and make the first row
        # 'bold and italic.
        rows = len(data)
        cols = len(data[0])
        oTable = self.oDoc.Tables.Add(self.oDoc.Bookmarks.Item("\endofdoc").Range, rows, cols)
        # oTable.Range.ParagraphFormat.SpaceAfter = 6
        for r in range(1, rows + 1):
            for c in range(1, cols + 1):
                print(r-1, c-1)
                oTable.Cell(r, c).Range.Text = str(data[r-1, c-1])
        # oTable.Rows.Item(1).Range.Font.Bold = True
        oTable.Rows.Item(1).Range.Font.Italic = True
        self.make_normal_text("", size=self.smallfont)

    def make_table_struct(self, headers, data):
        # 'Insert a table, fill it with data, and make the first row
        # 'bold and italic.
        if len(data.shape) == 1:
            rows = 2
        else:
            rows = len(data) + 1
        cols = len(headers)
        oTable = self.oDoc.Tables.Add(self.oDoc.Bookmarks.Item("\endofdoc").Range, rows, cols)
        # oTable.Range.ParagraphFormat.SpaceAfter = 6
        for c in range(1, cols+1):
            oTable.Cell(1, c).Range.Text = str(headers[c-1])
            if len(data.shape) == 1:
                oTable.Cell(2, c).Range.Text = str(data[c-1])
            else:
                for r in range(2, rows+1):
                    oTable.Cell(r, c).Range.Text = str(data[r-2][c-1])
        oTable.Rows.Item(1).Range.Font.Bold = True
        oTable.Rows.Item(1).Range.Font.Italic = True
        self.make_normal_text("", size=self.smallfont)

    def make_table_wts(self, client_wt_IDs, check_wt_IDs, check_set_file_path, std_wt_IDs, std_set_file_path):
        wtsTable = self.oDoc.Tables.Add(self.oDoc.Bookmarks.Item("\endofdoc").Range, 5, 2)
        wtsTable.Range.ParagraphFormat.SpaceAfter = 0
        wtsTable.Cell(1, 1).Range.Text = "Client weights:"
        wtsTable.Cell(1, 2).Range.Text = str(client_wt_IDs)
        wtsTable.Cell(2, 1).Range.Text = "Check weights:"
        wtsTable.Cell(2, 2).Range.Text = str(check_wt_IDs)
        wtsTable.Cell(3, 2).Range.Text = check_set_file_path
        wtsTable.Cell(4, 1).Range.Text = "Standard weights:"
        wtsTable.Cell(4, 2).Range.Text = str(std_wt_IDs)
        wtsTable.Cell(5, 2).Range.Text = std_set_file_path
        wtsTable.Columns.Autofit()
        self.make_normal_text("", size=self.smallfont)

    def make_table_wts_nochecks(self, client_wt_IDs, std_wt_IDs, std_set_file_path):
        wtsTable = self.oDoc.Tables.Add(self.oDoc.Bookmarks.Item("\endofdoc").Range, 4, 2)
        wtsTable.Range.ParagraphFormat.SpaceAfter = 0
        wtsTable.Cell(1, 1).Range.Text = "Client weights:"
        wtsTable.Cell(1, 2).Range.Text = str(client_wt_IDs)
        wtsTable.Cell(2, 1).Range.Text = "Check weights:"
        wtsTable.Cell(2, 2).Range.Text = 'None'
        wtsTable.Cell(3, 1).Range.Text = "Standard weights:"
        wtsTable.Cell(3, 2).Range.Text = str(std_wt_IDs)
        wtsTable.Cell(4, 2).Range.Text = std_set_file_path
        wtsTable.Columns.Autofit()

    def make_table_massdata(self, data, masscol=None):
        """Makes table of structured data containing one column of mass data to be formatted in 'Greg' formatting"""
        headers = data.metadata.get('metadata')['headers']
        if len(data.shape) == 1:
            rows = 2
        else:
            rows = len(data) + 1
        cols = len(headers)
        oTable = self.oDoc.Tables.Add(self.oDoc.Bookmarks.Item("\endofdoc").Range, rows, cols)
        oTable.Range.ParagraphFormat.SpaceAfter = 0
        for c in range(1, cols+1):
            oTable.Cell(1, c).Range.Text = str(headers[c-1])
            if len(data.shape) == 1:
                if c == masscol:
                    print()
                    oTable.Cell(2, c).Range.Text = greg_format(data[c - 1])
                    oTable.Cell(2, c).Range.ParagraphFormat.Alignment = 2
                #     https://docs.microsoft.com/en-us/dotnet/api/microsoft.office.interop.word.wdparagraphalignment?view=word-pia
                else:
                    oTable.Cell(2, c).Range.Text = str(data[c-1])
            else:
                for r in range(2, rows+1):
                    if c == masscol:
                        oTable.Cell(r, c).Range.Text = greg_format(data[r - 2][c - 1])
                        oTable.Cell(r, c).Range.ParagraphFormat.Alignment = 2
                    else:
                        oTable.Cell(r, c).Range.Text = str(data[r-2][c - 1])
                    # oTable.Cell(r, c).Range.Text = str(data[r-2][c-1])
        oTable.Rows.Item(1).Range.Font.Bold = True
        oTable.Rows.Item(1).Range.Font.Italic = True
        oTable.Range.Font.Size = self.smallfont
        oTable.Columns.Autofit()
        self.make_normal_text("", size=self.smallfont)

    def add_weighing_scheme(self, scheme, fmc_root, check_file, std_file):
        client_wt_IDs = list_to_csstr(fmc_root["1: Mass Sets"]["Client"].metadata.get("client weight ID"))
        if check_file:
            checks = {
                'weight ID': list_to_csstr(fmc_root["1: Mass Sets"]["Check"].metadata.get("check weight ID")),
                'Set file': check_file
            }
        else:
            checks = None
        std_wts = list_to_csstr(fmc_root["1: Mass Sets"]["Standard"].metadata.get("std weight ID"))

        self.make_heading1('Weighing Scheme')
        headers = ['Weight groups', 'Nominal mass(g)', 'Balance alias', '# runs']
        self.make_table_struct(headers, scheme)
        if checks is not None:
            self.make_table_wts(client_wt_IDs, checks['weight ID'], checks['Set file'], std_wts, std_file)
        else:
            self.make_table_wts_nochecks(client_wt_IDs, std_wts, std_file)

    def add_mls(self, fmc_root):
        """Adds matrix least squares section to summary file"""
        self.make_heading1('Matrix Least Squares Analysis')
        timestamp = fmc_root['metadata'].metadata['Timestamp'].split()
        self.make_normal_text('Date: ' + timestamp[0] + '\tTime: ' + timestamp[1])

        self.make_heading2('Input data')
        input_data = fmc_root['2: Matrix Least Squares Analysis']["Input data with least squares residuals"]
        self.make_table_massdata(input_data, 3)
        save_mls_excel(input_data)

        self.make_heading2('Mass values from Least Squares solution')
        mvals = fmc_root['2: Matrix Least Squares Analysis']["Mass values from least squares solution"]
        h2 = mvals.metadata.get('metadata')['headers']
        self.make_table_massdata(mvals, 4)
        meta = fmc_root['2: Matrix Least Squares Analysis']['metadata'].metadata
        self.make_normal_text(
                "Number of observations = " + str(meta['Number of observations']) +
                ", Number of unknowns = " + str(meta['Number of unknowns']) +
                ", Degrees of freedom = " + str(meta['Degrees of freedom']) +
                ", \nRelative uncertainty for no buoyancy correction (ppm) = " + str(meta['Relative uncertainty for no buoyancy correction (ppm)']) +
                ", \nSum of residues squared (ug^2) = " + str(meta['Sum of residues squared ('+MU_STR+'g^2)'])
        )
        self.page_break()

    def make_table_run_meta(self, cw_run_meta):
        """Makes table of ambient and other metadata from circular weighing run"""
        runTable = self.oDoc.Tables.Add(self.oDoc.Bookmarks.Item("\endofdoc").Range, 2, 8) # 1 = autofit, 0 not
        runTable.Range.ParagraphFormat.SpaceAfter = 0
        runTable.Cell(1, 1).Range.Text = 'Time:'
        runTable.Cell(1, 2).Range.Text = cw_run_meta.get("Mmt Timestamp").split()[1]
        runTable.Cell(1, 3).Range.Text = 'Date:'
        runTable.Cell(1, 4).Range.Text = cw_run_meta.get("Mmt Timestamp").split()[0]
        runTable.Cell(1, 5).Range.Text = "Balance:"
        runTable.Cell(1, 6).Range.Text = cw_run_meta.get("Balance")
        runTable.Cell(1, 7).Range.Text = 'Unit:'
        runTable.Cell(1, 8).Range.Text = cw_run_meta.get("Unit")
        runTable.Cell(2, 1).Range.Text = "Temp (°C):"
        runTable.Cell(2, 2).Range.Text = cw_run_meta.get("T"+IN_DEGREES_C)
        runTable.Cell(2, 3).Range.Text = "RH (%):"
        runTable.Cell(2, 4).Range.Text = cw_run_meta.get("RH (%)")
        runTable.Cell(2, 5).Range.Text = "Ambient OK?"
        runTable.Cell(2, 6).Range.Text = str(cw_run_meta.get("Ambient OK?"))
        runTable.Range.Font.Size = self.smallfont
        runTable.Columns.Autofit()

    def make_table_diffs_meta(self, cw_anal_meta):
        '''Makes table of metadata from circular weighing analysis'''
        table = self.oDoc.Tables.Add(self.oDoc.Bookmarks.Item("\endofdoc").Range, 4, 2) # 1 = autofit, 0 not
        table.Range.ParagraphFormat.SpaceAfter = 0
        table.Cell(1, 1).Range.Text = 'Analysis uses times?'
        table.Cell(1, 2).Range.Text = str(cw_anal_meta.get("Uses mmt times"))
        table.Cell(2, 1).Range.Text = "Residual std devs:"
        res_dict = cw_anal_meta.get("Residual std devs")
        table.Cell(2, 2).Range.Text = res_dict.strip("{").strip("}")
        table.Cell(3, 1).Range.Text = 'Selected drift:'
        table.Cell(3, 2).Range.Text = cw_anal_meta.get("Selected drift")
        table.Cell(4, 1).Range.Text = "Drift components ("+ cw_anal_meta.get("Drift unit") + "):"
        drifts = ""
        try:
            drifts += 'linear drift:\t' + cw_anal_meta.get("linear drift")
            drifts += '\nquadratic drift:\t' + cw_anal_meta.get("quadratic drift")
            drifts += '\ncubic drift:\t' + cw_anal_meta.get("cubic drift")
        except TypeError:
            pass
        table.Cell(4, 2).Range.Text = drifts
        table.Range.Font.Size = self.smallfont
        table.Columns.Autofit()

    def make_table_cwdata(self, wtpos, weighdata):
        '''Makes table of raw circular weighing data with headings '(position) weight group',
        and data as twin columns of times and balance readings

        Parameters
        ----------
        wtpos : list of weight groups and positions as tuples
        weighdata : structured array
        '''
        rows = len(weighdata) + 1
        cols = len(wtpos) * 2
        oTable = self.oDoc.Tables.Add(self.oDoc.Bookmarks.Item("\endofdoc").Range, rows, cols)
        # oTable.Range.ParagraphFormat.SpaceAfter = 6
        for c in range(len(wtpos)):
            oTable.Cell(1, 2*c+1).Range.Text = "(" + str(wtpos[c][1]) + ") " + str(wtpos[c][0])
            # oTable.Cell(1, 2*(c + 1)).Range.Text = str(wtpos[c][1])
            for r in range(2, rows+1):
                oTable.Cell(r, 2 * c + 1).Range.Text = '{:.2f}'.format(weighdata[r-2][c][0])
                oTable.Cell(r, 2 * (c + 1)).Range.Text = '{:.6g}'.format(weighdata[r-2][c][1])
        oTable.Rows.Item(1).Range.Font.Bold = True
        oTable.Rows.Item(1).Range.Font.Italic = True

        oTable.Range.Font.Size = self.smallfont
        oTable.Columns.Autofit()

        for c in range(len(wtpos)):
            myCells = self.oDoc.Range(oTable.Cell(1, c+1).Range.Start, oTable.Cell(1, c+2).Range.End)
            myCells.Cells.Merge()
            # https://docs.microsoft.com/en-us/office/vba/api/word.cells.merge

        oTable.Rows.Item(1).Range.ParagraphFormat.Alignment = 1
        oTable.Borders.Enable = True

    def make_table_cw_diffs(self, data):
        """Makes table of differences e.g. position 0 - position 1, mass difference, residual.
        Uses original units from weighing."""
        headers = ["+ weight group", "- weight group", "mass difference", "residual"]
        rows = len(data) + 1
        cols = len(headers)
        oTable = self.oDoc.Tables.Add(self.oDoc.Bookmarks.Item("\endofdoc").Range, rows, cols)
        oTable.Range.ParagraphFormat.SpaceAfter = 0
        for c in range(1, cols + 1):
            oTable.Cell(1, c).Range.Text = str(headers[c - 1])
            for r in range(2, rows + 1):
                if c > 2:
                    oTable.Cell(r, c).Range.Text = '{:.7f}'.format(data[r - 2][c - 1])
                    oTable.Cell(r, c).Range.ParagraphFormat.Alignment = 2
                else:
                    oTable.Cell(r, c).Range.Text = str(data[r - 2][c - 1])
        oTable.Rows.Item(1).Range.Font.Bold = True
        oTable.Rows.Item(1).Range.Font.Italic = True

        oTable.Range.Font.Size = self.smallfont
        oTable.Columns.Autofit()

    def add_weighing_dataset(self, cw_file, se, nom, incl_datasets):
        """How to add a dataset from a single circular weighing"""
        if not os.path.isfile(cw_file):
            print('No data yet collected for '+se)
        else:
            self.make_heading2(se)
            print('Reading '+cw_file)
            root = read(cw_file)
            wt_grps = se.split()

            for dataset in root['Circular Weighings'][se].datasets():
                dname = dataset.name.split('_')
                ambient = False

                if dname[0][-8:] == 'analysis':
                    run_id = 'run_' + dname[2]
                    if (str(float(nom)), se, dname[2]) in incl_datasets:
                        self.make_heading3(run_id)
                        ambient = True
                    else:
                        self.make_heading3(run_id + "(EXCLUDED)")

                    weighdata = root.require_dataset(
                        root['Circular Weighings'][se].name + '/measurement_' + run_id)
                    # self.make_heading4('Metadata')
                    self.make_table_run_meta(weighdata.metadata)

                    if ambient:
                        temps = weighdata.metadata.get("T"+IN_DEGREES_C).split(" to ")
                        for t in temps:
                            self.collate_ambient['T' + IN_DEGREES_C].append(float(t))
                        rhs = weighdata.metadata.get("RH (%)").split(" to ")
                        for rh in rhs:
                            self.collate_ambient['RH (%)'].append(float(rh))

                    self.make_heading4('Balance readings')
                    self.make_normal_text('Note times are in minutes; weighing positions are in brackets.')

                    wtpos = []
                    try:
                        for i in range(1, len(wt_grps) + 1):
                            a = weighdata.metadata.get("grp"+str(i)).split() # old way of recording groups
                            wtpos.append([a[0], a[-1]])
                    except AttributeError:
                        d = weighdata.metadata.get("Weight group loading order") # new way of recording groups
                        for key, value in d.items():
                            wtpos.append([value, key.strip("Position ")])
                    self.make_table_cwdata(wtpos, weighdata)

                    self.make_heading4('Column average differences')
                    analysisdata = root.require_dataset(
                        root['Circular Weighings'][se].name + '/analysis_' + run_id)
                    self.make_table_cw_diffs(analysisdata.data)
                    self.make_normal_text(" ", self.smallfont)
                    self.make_table_diffs_meta(analysisdata.metadata)

    def add_weighing_datasets(self, client, folder, scheme, incl_datasets):
        self.make_heading1("Circular Weighing Data")
        if len(scheme.shape) == 1:
            se = scheme[0]
            nom = scheme[1]
            cw_file = os.path.join(folder, client + '_' + nom + '.json')
            self.add_weighing_dataset(cw_file, se, nom, incl_datasets)
        else:
            for row in range(len(scheme.shape)):
                se = scheme[row][0]
                nom = scheme[row][1]
                cw_file = os.path.join(folder, client + '_' + nom + '.json')
                if not os.path.isfile(cw_file):
                    print('No data yet collected for ' + se)
                else:
                    self.add_weighing_dataset(cw_file, se, nom, incl_datasets)

        self.make_heading2("Overall ambient conditions for included weighings")
        self.make_normal_text(
            "T"+IN_DEGREES_C+":\t" + str(min(self.collate_ambient["T"+IN_DEGREES_C])) + " to " + str(max(self.collate_ambient["T"+IN_DEGREES_C]))
        )
        self.make_normal_text(
            "RH (%):\t" + str(round(min(self.collate_ambient["RH (%)"]), 1)) + " to " + str(round(max(self.collate_ambient["RH (%)"]), 1))
        )


