import os
import contextvars

config = contextvars.ContextVar(
    'config',
    default=os.path.abspath(os.path.join(
        r'C:\Users\r.hawke.IRL\PycharmProjects\Mass-Circular-Weighing', 'config.xml'))
)

cfg = contextvars.ContextVar('cfg', default=None)

folder = contextvars.ContextVar(
    'Folder',
    default=r'I:\MSL\Private\Mass\transfer\Balance Software\Sample Data'
)

job = contextvars.ContextVar('Job', default="WOW!")
client = contextvars.ContextVar('Client', default=' ')
client_wt_IDs = contextvars.ContextVar('Client wt IDs', default='1 2 5 10 20 50 100 200 500 1000 2000 5000')

stds = contextvars.ContextVar('stds')
checks = contextvars.ContextVar('checks')

drift = contextvars.ContextVar('drift')
timed = contextvars.ContextVar('timed', default=False)
correlations = contextvars.ContextVar('correlations')

incl_datasets = contextvars.ContextVar('incl datasets')