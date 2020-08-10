"""SSH ulitities setup script."""

from pathlib import Path

from setuptools import find_packages, setup

# The directory containing this file
PKG_ROOT = Path(__file__).parent

# Read package constants
README = (PKG_ROOT / "README.rst").read_text()
VERSION = ((PKG_ROOT / "ssh_utilities" / "version.py")
           .read_text().split(" = ")[1].replace("\"", ""))
REQUIREMENTS = (PKG_ROOT / "requirements.txt").read_text().splitlines()

if not Path("~/.ssh/config").expanduser().is_file():
    print("No config file was found in ~/.ssh directory, please configure"
          " ssh_config.json or put the config file in ~/.ssh directory if"
          " you want to use ssh functionallity to full potential")

setup(
    name="ssh_utilities",
    version=VERSION,
    description="paramiko convenience wrapper",
    long_description=README,
    long_description_content_type="text/x-rst",
    url="https://github.com/marian-code/ssh-utilities",
    author="Marián Rynik",
    author_email="marian.rynik@outlook.sk",
    license="LGPL-2.1",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Utilities",
        "Topic :: Internet",
        "Typing :: Typed",
    ],
    packages=find_packages(exclude=("tests",)),
    include_package_data=True,
    install_requires=REQUIREMENTS,
    extras_require={"test": ["unittest"] + REQUIREMENTS}
)
