"""
A helper script to extract a table of weighing times for consecutive runs.
Used to assess the timing consistency of the new automatic weight changer.
"""

from msl.io import read
import xlwt

json_file = r'I:\MSL\Private\Mass\Balances\XPE505C\Testing in mass lab\20200930\Mass Lab_500.json'

jf = read(json_file)
print(jf)

book = xlwt.Workbook(encoding="utf-8")

sheet1 = book.add_sheet("Sheet 1")

for data_set in jf.datasets():
    if 'measurement' in data_set.name:
        if data_set.metadata.get("Weighing complete"):
            run_no = data_set.name.split('_')[-1]
            print(data_set.name, run_no)
            for cycle, cyc_val in enumerate(data_set):
                num_pos = len(cyc_val)
                for pos, reading_value in enumerate(cyc_val):
                    sheet1.write(cycle*num_pos+pos, int(run_no), reading_value[0])

book.save(r"I:\MSL\Private\Mass\Balances\XPE505C\Testing in mass lab\20200930\RawData_timemmts_500s_2-4.xls")