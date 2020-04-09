from src.configuration import Configuration



config = r'C:\Users\r.hawke\PycharmProjects\Mass-Circular-Weighing\config.xml'
### initialise application
cfg = Configuration(config)


omega = cfg.get_omega_instance('Omega')
ambient = omega.get_t_rh()

print(ambient)



