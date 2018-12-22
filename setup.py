from setuptools import setup, find_packages
exec(open('academictorrents/version.py').read())

with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='academictorrents',
    version=__version__,
    description='Academic Torrents Python APIs',
    long_description=readme,
    author='Martin Weiss, Alexis Gallepe, Jonathan Nogueira',
    author_email='contact@academictorrents.com',
    data_files = [("", ["LICENSE"])],
    url='https://github.com/AcademicTorrents/python-r-api',
    classifiers=(
        "Programming Language :: Python :: 2.6"
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.0",
        "Programming Language :: Python :: 3.1",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
    ),
    license=license,
    packages=find_packages(exclude=('tests', 'docs')),
    install_requires=[
        'bencode.py==2.0.0',
        'bitstring==3.1.5',
        'PyPubSub==3.3.0',
        'requests>=2.19.0',
        'future==0.16.0'
    ]
)
