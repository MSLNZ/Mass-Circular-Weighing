"""
Test communications with a Mettler Toledo balance by performing a repeatability check
"""

from time import sleep

from mass_circular_weighing.constants import config_default
from mass_circular_weighing.configuration import Configuration
from mass_circular_weighing.equip.mettler import MettlerToledo


cfg = config_default

app = Configuration(cfg)

bal, mode = app.get_bal_instance('LUCY')

print(bal.unit)
print(bal.mode)
print(bal.get_serial())


zeroes = []
masses = []
bal.load_bal('None', 1)
bal.zero_bal()
sleep(3)
# bal.scale_adjust()
# sleep(3)

bal.load_bal('None', 1)
z = bal.get_mass_stable('')
zeroes.append(z)
bal.unload_bal('None', 1)

for i in range(11):  # added an extra loading to exercise the balance
    bal.load_bal('Mass', 1)
    m = bal.get_mass_stable(str(i))
    masses.append(m)
    print(m)
    bal.unload_bal('Mass', 1)
    bal.load_bal('None', 1)
    z = bal.get_mass_stable('')
    zeroes.append(z)
    print(z)
    bal.unload_bal('None', 1)


# print(bal.unit)
for m in masses:
    print(m)
for z in zeroes:
    print(z)


bal.connection.disconnect()
