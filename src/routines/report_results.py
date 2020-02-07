from msl.loadlib import LoadLibrary


def checkable_summary(housekeeping, schemetable):
    com = LoadLibrary('Scripting.FileSystemObject', 'com')
    fp = com.lib.CreateTextFile('a_new_file.txt')
    fp.WriteLine('This is a test')

    fp.Close()
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

