import os
import contextvars

config = contextvars.ContextVar('cfg', default=os.path.abspath(os.path.join(
    r'C:\Users\r.hawke.IRL\PycharmProjects\Mass-Circular-Weighing', 'config.xml')))

folder = contextvars.ContextVar('Folder', default=r'I:\MSL\Private\Mass\transfer\Balance Software\Sample Data')

job = contextvars.ContextVar('Job')
client = contextvars.ContextVar('Client', default=' ')
client_masses = contextvars.ContextVar('client masses', default='1 2 5 10 20 50 100 200 500 1000 2000 5000')

stds = contextvars.ContextVar('stds')
checks = contextvars.ContextVar('checks')

drift = contextvars.ContextVar('drift')
timed = contextvars.ContextVar('timed', default=False)
correlations = contextvars.ContextVar('correlations')

