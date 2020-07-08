#!/usr/bin/env python

from setuptools import setup

readme = open("README.rst").read()

setup(name="hexfilter",
      version="0.2",
      description="A library/tool for extracting hex dumps from log files",
      url="https://github.com/erstrom/hexfilter",
      author="Erik Stromdahl",
      author_email="erik.stromdahl@gmail.com",
      license="MIT",
      long_description=readme + "\n\n",
      entry_points={
        "console_scripts": ["hexfilter=hexfilter.__main__:main"]
      },
      packages=["hexfilter"],
      classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.5",
        "Topic :: Software Development"
      ]
)
