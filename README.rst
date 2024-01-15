Python venv-autouse
###################

.. .. image:: https://github.com/XonqNopp/python-venv-autouse/actions/workflows/python-package.yml/flake8-badge.svg
   :target: https://github.com/XonqNopp/python-venv-autouse/actions/workflows/python-package.yml

.. image:: https://github.com/XonqNopp/python-venv-autouse/actions/workflows/python-package.yml/badge.svg
   :target: https://github.com/XonqNopp/python-venv-autouse/actions/workflows/python-package.yml

.. .. image:: https://github.com/XonqNopp/python-venv-autouse/actions/workflows/python-package.yml/tests-badge.svg
   :target: https://github.com/XonqNopp/python-venv-autouse/actions/workflows/python-package.yml

.. .. image:: https://github.com/XonqNopp/python-venv-autouse/actions/workflows/python-package.yml/coverage-badge.svg
   :target: https://github.com/XonqNopp/python-venv-autouse/actions/workflows/python-package.yml

|

.. image:: https://img.shields.io/pypi/pyversions/venv-autouse.svg
    :target: https://pypi.org/project/venv-autouse/

.. image:: https://img.shields.io/pypi/v/venv-autouse
   :target: https://pypi.org/project/venv-autouse/


This package helps managing venv in different locations for different scripts.
You don't have to manually care about calling a script with the according venv.
All you need is provide a requirements file and import this module in the files which require the venv.
This module needs to be installed system-wide or in every venv you use to call files.
However, if you are executing files from within a venv, you will loose the current venv.

The versioning follows `semantic versioning <http://semver.org>`_.


File
****

When you have a python script ``file.py`` and it needs a venv, you can simply add ``import venv_autouse.file``
at the top of the file, and write the requirements file ``file.req.txt``.
It also uses the ``requirements.txt`` file in the directory of the file.
All this will create a venv directory ``.file.venv`` in the same directory.


Directory
*********

This is the same, except that it uses a venv shared in the directory of the file to save space when possible.
