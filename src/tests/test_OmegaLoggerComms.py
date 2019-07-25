from src.application import Application



config = r'C:\Users\r.hawke\PycharmProjects\Mass-Circular-Weighing\config.xml'
### initialise application
app = Application(config)


omega = app.get_omega_instance('Omega')
ambient = omega.get_t_rh_dp()

print(ambient)



