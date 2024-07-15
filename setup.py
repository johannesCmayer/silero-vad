#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='silero-vad',
      version='1.0',
      # Modules to import from other scripts:
      packages=find_packages(),
      # Executables
      entry_points = {
          'console_scripts': [
              "silero-vad = vad.vad:main",
          ],
      },
)
