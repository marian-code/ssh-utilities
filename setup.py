"""SSH ulitities setup script."""

from setuptools import setup, find_packages
import os

# The directory containing this file
HERE = os.path.dirname(os.path.realpath(__file__))

if not os.path.isfile(os.path.expanduser("~/.ssh/config")):
    print("No config file was found in ~/.ssh directory, please configure"
          " ssh_config.json or put the config file in ~/.ssh directory if"
          " you want to use ssh functionallity to full potential")

setup(
    name="ssh_utilities",
    version="0.1.0",
    description="paramiko convenience wrapper",
    long_description="paramiko convenience wrapper",
    long_description_content_type="text/markdown",
    url="https://github.com/marian-code/ssh-utilities",
    author="Marián Rynik",
    author_email="rynik1@uniba.sk",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
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
    install_requires=["paramiko"]
)
