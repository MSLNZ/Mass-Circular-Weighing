"""
Test communications with a Mettler Toledo balance by performing a repeatability check
"""

from time import sleep

from mass_circular_weighing.configuration import Configuration
from mass_circular_weighing.equip.mettler import MettlerToledo


cfg = r'C:\Users\r.hawke\PycharmProjects\Mass-Circular-Weighing\config.xml'

app = Configuration(cfg)

bal, mode = app.get_bal_instance('K_C')

print(bal.unit)
print(bal.mode)
print(bal.get_serial())



zeroes = []
masses = []
bal.load_bal('None', 1)
bal.zero_bal()
sleep(3)
z = bal.get_mass_stable('')
zeroes.append(z)
bal.unload_bal('None', 1)

for i in range(10):
    bal.load_bal('Mass', 1)
    m = bal.get_mass_stable(str(i))
    masses.append(m)
    bal.unload_bal('Mass', 1)
    bal.load_bal('None', 1)
    z = bal.get_mass_stable('')
    zeroes.append(z)
    bal.unload_bal('None', 1)


# print(bal.unit)
for m in masses:
    print(m)
for z in zeroes:
    print(z)


bal.connection.disconnect()



# bal.scale_adjust()
'''
bal.tare_bal()
'''
