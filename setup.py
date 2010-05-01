#!/usr/bin/env python
from distutils.core import setup
from mutant import __version__

long_description = open('README.rst').read()

setup(name='mutant',
      version=__version__,
      py_modules=['mutant'],
      description="Mutation testing for Python",
      author="Michael Stephens",
      author_email="me@mikej.st",
      license="BSD",
      url="http://github.com/mikejs/mutant",
      long_description=long_description,
      platforms=["any"],
      classifiers=["Development Status :: 4 - Beta",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: BSD License",
                   "Natural Language :: English",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python",
                   "Topic :: Software Development :: Libraries :: Python Modules",
                   ],
      )
