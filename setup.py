from setuptools import setup, find_packages

exec(open("academictorrents/version.py").read())

with open("README.md") as f:
    readme = f.read()

setup(
    name="academictorrents",
    version=__version__,
    description="Academic Torrents Python API",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Martin Weiss, Alexis Gallepe, Jonathan Nogueira, Joseph Paul Cohen",
    author_email="contact@academictorrents.com",
    url="https://github.com/AcademicTorrents/at-python",
    classifiers=(
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
    ),
    python_requires=">=3.10",
    license="MIT",
    license_files=["LICENSE"],
    packages=find_packages(exclude=("tests", "tests.*", "docs")),
    install_requires=[
        "bencode.py>=2.0.0",
        "requests>=2.19.0",
        "urllib3",
        "tqdm",
    ],
    entry_points={
        "console_scripts": ["at-get = academictorrents:cli"],
    },
)
