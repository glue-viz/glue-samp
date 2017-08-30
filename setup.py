#!/usr/bin/env python

from __future__ import print_function

from setuptools import setup, find_packages

entry_points = """
[glue.plugins]
samp=glue_samp:setup
"""

with open('README.rst') as infile:
    LONG_DESCRIPTION = infile.read()

with open('glue_samp/version.py') as infile:
    exec(infile.read())

setup(name='glue-samp',
      version=__version__,
      description='A SAMP plugin for glue',
      long_description=LONG_DESCRIPTION,
      url="https://github.com/glue-viz/glue-samp",
      author='Thomas Robitaille',
      author_email='thomas.robitaille@gmail.com',
      packages = find_packages(),
      package_data={},
      entry_points=entry_points
    )
