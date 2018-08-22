# Copyright 2018, Simon Kennedy, sffjunkie+code@gmail.com

import io
import os
from setuptools import setup

import monkeypatch # pylint: disable=W0611

def read_contents(*names, **kwargs):
    return io.open(
        os.path.join(*names),
        encoding=kwargs.get("encoding", "utf8")
    ).read()

description = 'A light and fluffy serving of Cheese.'
try:
    long_description = read_contents(os.path.dirname(__file__), 'README.rst')
except:
    long_description = description

setup(name='souffle',
      version='0.1',
      description=description,
      long_description=long_description,
      author='Simon Kennedy',
      author_email='sffjunkie+code@gmail.com',
      url="https://github.com/sffjunkie/souffle",
      project_urls={
          'Documentation': 'https://souffle.readthedocs.io/en/stable/index.html',
          'Source': 'https://github.com/sffjunkie/souffle',
          'Issues': 'https://github.com/sffjunkie/souffle/issues',
      },
      license='Apache-2.0',
      classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
      ],
      package_dir={'': 'src'},
      py_modules=['souffle'],
      tests_require=['pytest-runner'],
)
