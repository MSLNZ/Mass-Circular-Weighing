from msl.loadlib import LoadLibrary #, utils
# info = utils.get_com_info()
# for key, value in info.items():
#     if 'Microsoft' in value['ProgID']:
#         print(key, value)

# https://docs.microsoft.com/en-us/office/vba/api/word.application
# https://support.microsoft.com/en-nz/help/316383/how-to-automate-word-from-visual-basic-net-to-create-a-new-document

class WordDoc(object):
    def __init__(self):
        # Start Word and open the document template.
        self.oWord  = LoadLibrary('Word.Application', 'com').lib
        self.oWord.Visible = True
        self.oDoc = self.oWord.Documents.Add()

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

    def make_normal_text(self, text):
        #Insert another paragraph.
        oPara2t = self.oDoc.Content.Paragraphs.Add()
        oPara2t.Range.Text = text
        oPara2t.Format.SpaceAfter = 0   # 0 pt spacing after paragraph.
        oPara2t.Range.InsertParagraphAfter()

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
        self.make_normal_text("")

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
        self.make_normal_text("")

    def make_table_wts(self, client_wt_IDs, check_wt_IDs, check_set_file_path, std_wt_IDs, std_set_file_path):
        wtsTable = self.oDoc.Tables.Add(self.oDoc.Bookmarks.Item("\endofdoc").Range, 5, 2)
        # wtsTable.Range.ParagraphFormat.SpaceAfter = 6
        wtsTable.Cell(1, 1).Range.Text = "Client weights:"
        wtsTable.Cell(1, 2).Range.Text = client_wt_IDs
        wtsTable.Cell(2, 1).Range.Text = "Check weights:"
        wtsTable.Cell(2, 2).Range.Text = check_wt_IDs
        wtsTable.Cell(3, 2).Range.Text = check_set_file_path
        wtsTable.Cell(4, 1).Range.Text = "Standard weights:"
        wtsTable.Cell(4, 2).Range.Text = std_wt_IDs
        wtsTable.Cell(5, 2).Range.Text = std_set_file_path
        wtsTable.Columns.Autofit()
        self.make_normal_text("")

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
        self.make_title("Summary of Calibration " + job + " for " + client)
        self.make_normal_text("Data files may be found in " + folder)

    def add_weighing_scheme(self, scheme, client_wt_IDs, check_wt_IDs, check_set_file_path, std_wt_IDs, std_set_file_path):
        self.make_heading1('Weighing Scheme')
        headers = ['Weight groups', 'Nominal mass(g)', 'Balance alias', '# runs']
        self.make_table_struct(headers, scheme)
        self.make_table_wts(client_wt_IDs, check_wt_IDs, check_set_file_path, std_wt_IDs, std_set_file_path)

    def add_mls(self, fmc_root):
        print(fmc_root)
        self.make_heading1('Matrix Least Squares Analysis')
        timestamp = fmc_root['metadata'].metadata['Timestamp'].split()
        self.make_normal_text('Date: ' + timestamp[0] + '\tTime: ' + timestamp[1])

        self.make_heading2('Input data')
        input_data = fmc_root['2: Matrix Least Squares Analysis']["Input data with least squares residuals"]
        h1 = input_data.metadata.get('metadata')['headers']
        self.make_normal_text('Overall ambient conditions: [temp_range, humidity_range]')
        self.make_table_struct(h1, input_data)

        self.make_heading2('Mass values from Least Squares solution')
        mvals = fmc_root['2: Matrix Least Squares Analysis']["Mass values from least squares solution"]
        h2 = mvals.metadata.get('metadata')['headers']
        self.make_table_struct(h2, mvals)
        meta = fmc_root['2: Matrix Least Squares Analysis']['metadata'].metadata
        print(meta)
        self.make_normal_text(
                "Number of observations = " + str(meta['Number of observations']) +
                ", Number of unknowns = " + str(meta['Number of unknowns']) +
                ", Degrees of freedom = " + str(meta['Degrees of freedom']) +
                ", \nRelative uncertainty for no buoyancy correction (ppm) = " + str(meta['Relative uncertainty for no buoyancy correction (ppm)']) +
                ", \nSum of residues squared (ug^2) = " + str(meta['Sum of residues squared (ug^2)'])
        )
        self.page_break()

    def make_table_run_meta(self, cw_root):
        runTable = self.oDoc.Tables.Add(self.oDoc.Bookmarks.Item("\endofdoc").Range, 2, 8) # 1 = autofit, 0 not
        runTable.Range.ParagraphFormat.SpaceAfter = 0
        runTable.Cell(1, 1).Range.Text = 'Time:'
        runTable.Cell(1, 2).Range.Text = ""
        runTable.Cell(1, 3).Range.Text = 'Date:'
        runTable.Cell(1, 4).Range.Text = ""
        runTable.Cell(1, 5).Range.Text = "Balance:"
        runTable.Cell(1, 6).Range.Text = ""
        runTable.Cell(1, 7).Range.Text = 'Unit:'
        runTable.Cell(1, 8).Range.Text = ""
        runTable.Cell(2, 1).Range.Text = "Temp (°C):"
        runTable.Cell(2, 2).Range.Text = ""
        runTable.Cell(2, 3).Range.Text = "RH (%):"
        runTable.Cell(2, 4).Range.Text = ""
        runTable.Cell(2, 5).Range.Text = "Ambient OK?:"
        runTable.Cell(2, 6).Range.Text = "False"
        runTable.Columns.Autofit()

    def make_table_diffs_meta(self, cw_root):
        table = self.oDoc.Tables.Add(self.oDoc.Bookmarks.Item("\endofdoc").Range, 4, 2) # 1 = autofit, 0 not
        table.Range.ParagraphFormat.SpaceAfter = 0
        table.Cell(1, 1).Range.Text = 'Analysis uses times?'
        table.Cell(1, 2).Range.Text = ""
        table.Cell(2, 1).Range.Text = "Residual std devs:"
        table.Cell(2, 2).Range.Text = ""
        table.Cell(3, 1).Range.Text = 'Selected drift:'
        table.Cell(3, 2).Range.Text = ""
        table.Cell(4, 1).Range.Text = "Drift components:"
        table.Cell(4, 2).Range.Text = ""
        table.Columns.Autofit()

    def add_weighing_datasets(self):
        self.make_heading1("Included Weighings")
        for se in ['se1', 'se2', 'se3', ]:
            self.make_heading2(se)
            for run in se:
                flag = 'Included'
                if flag == 'Excluded':
                    self.make_heading3(run + " (Excluded)")
                else:
                    self.make_heading3(run)
                self.make_heading4('Metadata')
                self.make_table_run_meta('blah')

                self.make_heading4('Balance readings')
                self.make_normal_text('Note times are in minutes; weighing positions are in brackets.')
                self.make_normal_text('here put [balance_readings_table]  ')

                self.make_heading4('Column average differences')
                self.make_normal_text('here put [differences_table]  ')
                self.make_table_diffs_meta('balhblah')
                self.make_normal_text("")

        # inc_datasets = self.inputdata_table.included_datasets
        # for tuple in inc_datasets:
        #     path = os.path.join(self.fmc_info['Folder'], self.fmc_info['Client'] + tuple[0])
        #     print(path)


