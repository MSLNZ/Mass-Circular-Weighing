"""Go through all folders and delete the automatically created 'backup' files and folders
   NB: once run, these files are gone!"""

import os
import stat

folder = r'I:\MSL\Private\Mass\Commercial Calibrations'

for flist in os.walk(folder):                   # traverse all folders and subfolders
    if 'backup' in flist[0]:                    # find the ones called 'backup'
        for f_name in flist[2]:                 # iterate through the files
            if 'backup' in f_name:
                backupfile = os.path.join(flist[0], f_name)
                print(backupfile)               # print which file is being deleted
                try:
                    os.remove(backupfile)               # delete the backup file if allowed
                except PermissionError:                 # e.g. the Excel Summary file backups
                    os.chmod(backupfile, stat.S_IWRITE) # change to write permission
                    os.remove(backupfile)               # delete the backup file

        # delete the empty backups folders
        print(flist[0])
        try:
            os.rmdir(flist[0])
        except OSError as e:
            print(e)
