=========
hexfilter
=========

hexfilter is a tool for filtering out hex dumps from log files.
The current version supports filtering of hex dumps obtained from the
print_hex_dump function in the linux kernel.

The purpose of the tool is to extract the hex dumps from a log file
and write those dumps into another file using a common format.
The produced output can be compared with other outputs using a diff tool
(such as beyond compare, winmerge, meld etc.)

* GitHub: https://github.com/erstrom/hexfilter

Features
--------

- Support for extracting hex dumps produced by linux print_hex_dump


Installing
----------

.. code-block:: bash

    $ git clone https://github.com/erstrom/hexfilter.git
    $ cd hexfilter
    $ sudo python setup.py install


Usage
-----

Run the tool with --help argument to list available options.

Example 1
^^^^^^^^^

Let's assume you have two drivers (running on two different machines) producing
log data containing hex dumps.

Below is an extract from driver A:

::

    Jul 15 17:25:56 xenial kernel: [272190.595082] SDIO TX 00000060: 02 00 00 00 10 08 40 00 08 00 00 00              ......@.....

And here is an extract from driver B:

::

    [  410.085422] sdio wr 00000060: 02 00 00 00 10 08 40 00 08 00 00 00              ......@.....

You would like to verify that the different drivers transmits the same data on
the SDIO interface.

Comparing the log files with a diff tool without any filtering would result in
a lot of differences even though the actual hex data is the same.

The actual filtering looks like this:

.. code-block:: bash

    $ python hexfilter -i log1 -s > log1.filtered
    $ python hexfilter -i log2 -s > log2.filtered
    $ vimdiff log1.filtered log2.filtered # Use preferred diff tool

Since hexfilter was invoked with the -s option, all timestamps was removed.
The filtered data in the above example would look like this for both log files:

::

    00000060: 02 00 00 00 10 08 40 00 08 00 00 00              ......@.....

The above result will make the diff tool not show any differences.
Only when the hex dump data differs, will it be detected by the diff tool.
This will make it a lot easier to spot "real" differences in the data.

