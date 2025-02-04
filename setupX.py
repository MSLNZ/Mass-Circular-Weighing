import os
import re
import subprocess
import sys

from setuptools import (
    Command,
    find_packages,
    setup,
)


class ApiDocs(Command):
    """
    A custom command that calls sphinx-apidoc
    see: https://www.sphinx-doc.org/en/latest/man/sphinx-apidoc.html
    """
    description = 'builds the api documentation using sphinx-apidoc'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        command = [
            None,  # in Sphinx < 1.7.0 the first command-line argument was parsed, in 1.7.0 it became argv[1:]
            '--force',  # overwrite existing files
            '--module-first',  # put module documentation before submodule documentation
            '--separate',  # put documentation for each module on its own page
            '-o', './docs/_autosummary',  # where to save the output files
            'mass_circular_weighing',  # the path to the Python package to document
        ]

        import sphinx
        if sphinx.version_info[:2] < (1, 7):
            from sphinx.apidoc import main
        else:
            from sphinx.ext.apidoc import main  # Sphinx also changed the location of apidoc.main
            command.pop(0)

        main(command)
        sys.exit(0)


class BuildDocs(Command):
    """
    A custom command that calls sphinx-build
    see: https://www.sphinx-doc.org/en/latest/man/sphinx-build.html
    """
    description = 'builds the documentation using sphinx-build'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import sphinx

        command = [
            None,  # in Sphinx < 1.7.0 the first command-line argument was parsed, in 1.7.0 it became argv[1:]
            '-b', 'html',  # the builder to use, e.g., create a HTML version of the documentation
            '-a',  # generate output for all files
            '-E',  # ignore cached files, forces to re-read all source files from disk
            'docs',  # the source directory where the documentation files are located
            './docs/_build/html',  # where to save the output files
        ]

        if sphinx.version_info[:2] < (1, 7):
            from sphinx import build_main
        else:
            from sphinx.cmd.build import build_main  # Sphinx also changed the location of build_main
            command.pop(0)

        build_main(command)
        sys.exit(0)


def read(filename):
    with open(filename) as fp:
        return fp.read()


def fetch_init(key):
    # open the __init__.py file to determine the value instead of importing the package to get the value
    init_text = read('mass_circular_weighing/__init__.py')
    return re.search(rf'{key}\s*=\s*(.*)', init_text).group(1).strip('\'\"')


def get_version():
    init_version = fetch_init('__version__')
    if 'dev' not in init_version:
        return init_version

    if 'develop' in sys.argv or ('egg_info' in sys.argv and '--egg-base' not in sys.argv):
        # then installing in editable (develop) mode
        #   python setupX.py develop
        #   pip install -e .
        suffix = 'editable'
    else:
        file_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            # write all error messages from git to devnull
            with open(os.devnull, 'w') as devnull:
                out = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=file_dir, stderr=devnull)
        except:
            try:
                git_dir = os.path.join(file_dir, '.git')
                with open(os.path.join(git_dir, 'HEAD')) as fp1:
                    line = fp1.readline().strip()
                    if line.startswith('ref:'):
                        _, ref_path = line.split()
                        with open(os.path.join(git_dir, ref_path)) as fp2:
                            sha1 = fp2.readline().strip()
                    else:  # detached HEAD
                        sha1 = line
            except:
                return init_version
        else:
            sha1 = out.strip().decode('ascii')

        suffix = sha1[:7]

    if init_version.endswith(suffix):
        return init_version

    # following PEP-440, the local version identifier starts with '+'
    return init_version + '+' + suffix


# specify the packages that mass-circular-weighing depends on
install_requires = [
    'msl-equipment @ https://github.com/MSLNZ/msl-equipment/archive/main.tar.gz',
    'msl-qt @ https://github.com/MSLNZ/msl-qt/archive/main.tar.gz',
    'msl-io @ https://github.com/MSLNZ/msl-io/archive/main.tar.gz',
    'msl-loadlib',  # used in Word file creation
    'msl-network',  # demo in services
    'PyQt5',     # if not already installed with msl-qt
    'requests',  # for communicating with Omega loggers via a web app
    'xlwt',      # still used in three modules (could re-write to use openpyxl)
    'xlrd',      # used in SchemeTable (could re-write to use openpyxl)
    'openpyxl>=3.1.5',  # for reading and writing Excel files. note version 3.1.2 caused issues
    'tabulate',  # for nice tables in LaTeX output
]
# 'xlrd<2.0' is required in msl-io to open both .xls and .xlsx files
# 'comtypes' isn't used anymore?

testing = {'test', 'tests'}.intersection(sys.argv)
pytest_runner = ['pytest-runner'] if testing else []

needs_sphinx = {'doc', 'docs', 'apidoc', 'apidocs'}.intersection(sys.argv)
sphinx = ['sphinx', 'sphinx_rtd_theme'] + install_requires if needs_sphinx else []

tests_require = ['pytest-cov']
if sys.version_info[:2] == (2, 7):
    tests_require.extend(['zipp<2.0.0', 'pytest<5.0'])
else:
    tests_require.append('pytest')

version = get_version()

setup(
    name='mass-circular-weighing',
    version=version,
    author=fetch_init('__author__'),
    author_email='info@measurement.govt.nz',
    url='https://github.com/MSLNZ/mass-circular-weighing',
    description='Mass-Circular-Weighing is a Python program intended for the calibration of masses '
                'at the Measurement Standards Laboratory of New Zealand.',
    long_description=read('README.rst'),
    platforms='any',
    license='MIT',
    classifiers=[],  # see https://pypi.python.org/pypi?%3Aaction=list_classifiers
    setup_requires=sphinx + pytest_runner,
    tests_require=tests_require,
    install_requires=install_requires,
    cmdclass={'docs': BuildDocs, 'apidocs': ApiDocs},
    packages=find_packages(include=('mass_circular_weighing*',)),
    include_package_data=True,  # includes all files specified in MANIFEST.in when building the distribution
    package_dir={'mass-circular-weighing': 'mass_circular_weighing'},
    entry_points={
        'console_scripts': [
            'mcw-gui = mass_circular_weighing.gui.gui:show_gui',
            'poll-omega-logger = mass_circular_weighing.utils.poll_omega_logger:poll_omega_logger',
            'circweigh-gui = mass_circular_weighing.utils.circweigh_subprocess:run_circweigh_popup',
        ],
    },
)

if 'dev' in version and not version.endswith('editable'):
    # ensure that the value of __version__ is correct if installing the package from a non-release code base
    init_path = ''
    if sys.argv[0] == 'setupX.py' and 'install' in sys.argv and not {'--help', '-h'}.intersection(sys.argv):
        # python setupX.py install
        try:
            cmd = [sys.executable, '-c', 'import mass_circular_weighing as p; print(p.__file__)']
            output = subprocess.check_output(cmd, cwd=os.path.dirname(sys.executable))
            init_path = output.strip().decode()
        except:
            pass
    elif 'egg_info' in sys.argv:
        # pip install
        init_path = os.path.dirname(sys.argv[0]) + '/mass_circular_weighing/__init__.py'

    if init_path and os.path.isfile(init_path):
        with open(init_path, mode='r+') as fp:
            source = fp.read()
            fp.seek(0)
            fp.write(re.sub(r'__version__\s*=.*', f"__version__ = '{version}'", source))
