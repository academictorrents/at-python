from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='academictorrents',
    version='0.2.0',
    description='Academic Torrents Python and R APIs',
    long_description=readme,
    author='Jonathan Nogueira, Martin Weiss',
    author_email='contact@academictorrents.com',
    url='https://github.com/AcademicTorrents/python-r-api',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)
