=========
hexfilter
=========

hexfilter is a tool for filtering out hex dumps from log files.
The current version supports filtering of hex dumps obtained from the
print_hex_dump* functions in the linux kernel.

The purpose of the tool is to extract hex dumps from a log file
and write those dumps into another file using a common format.
The produced output can be compared with other outputs using a diff tool
(such as beyond compare, winmerge, meld etc.)

* GitHub: https://github.com/erstrom/hexfilter

Installing
----------

.. code-block:: bash

    $ git clone https://github.com/erstrom/hexfilter.git
    $ cd hexfilter
    $ sudo python setup.py install

Running without installing
--------------------------

.. code-block:: bash

    $ git clone https://github.com/erstrom/hexfilter.git
    $ python hexfilter/hexfilter --help

Documentation
-------------

Documentation is available at http://hexfilter.readthedocs.io/en/latest/.

The documentation source is located in the ``docs/`` subdirectory and is
built with sphinx (http://www.sphinx-doc.org/en/stable/).

html documentation can be generated like this (see sphinx manual for more details):

.. code-block:: bash

    $ cd docs
    $ make html

The above commands require sphinx 1.0 or later.

The generated html will be available in:

``doc/_build/html/index.html``
