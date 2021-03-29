"""
A helper script to test communication with a Vaisala device
"""
from time import sleep

from mass_circular_weighing.constants import admin_default
from mass_circular_weighing.configuration import Configuration
from mass_circular_weighing.equip.ambient_checks import check_ambient_pre, check_ambient_post


app = Configuration(admin_default)
bal_alias = "MDE-demo"
# details for the MDE-demo balance will need to be altered to look for the Vaisala device rather than an Omega logger

mdebal, mode = app.get_bal_instance(bal_alias)

print(mode)
deets = mdebal.ambient_details
for key, value in deets.items():
    print(key, value)

vai = mdebal.ambient_instance

vai.open_comms()

vai.connection.write("?")
while True:
    ok = vai.connection.read()
    print(ok)
    if "module 2" in ok.lower():
        break

print("done")


ok = vai.set_format()


for r in range(5):
    print(vai.get_readings())
    sleep(2)

vai.close_comms()


# amb_pre = check_ambient_pre(ambient_instance=vai, ambient_details=deets)
#
# sleep(2)
#
# amb_post = check_ambient_post(amb_pre, ambient_instance=vai, ambient_details=deets)
#
#
