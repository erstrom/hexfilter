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
- Support for timestamp conversion/rounding of the hex dump logs in order to ease comparison


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

Example 2 (timing)
^^^^^^^^^^^^^^^^^^

Sometimes it is useful to compare the timing of different driver
implementations as well as the hex data.
(when was the command/message in the hex dump issued?).

Let's assume there are two driver implementations that issues
exactly the same commands (hex dumps are identical), but one of them works and
the other doesn't.

The most likely cause in this case is timing. Perhaps the target hardware is
timing out before a certain command is issued?

If the -s (or --skip-timestamps) option is omitted, hexfilter will read the
timestamps from the input file (assuming there are any) and convert them into
delta times that will be written to the output together with the hex dump.

The delta times are the time difference between the hex dumps.

.. IMPORTANT::
    Make sure the linux kernel was built with CONFIG_PRINTK_TIME, otherwise no
    timestamps will be added to the log!

Even if two drivers have more or less exactly the same timing, there will most
likely still be a small deviation between timestamps in the log. The linux
kernel printk timestamps have microsecond resolution, so most likely the last
decimals will be slightly different every time the driver code is executed.

In order to mitigate this problem, hexfilter can be invoked with the -r
(or --rounding) option. This will make the timestamp rounded to the nearest
rounding step specified by the option. The option takes a microsecond argument.

Let's take the same hex dumps as in Example 1 but without the -s option:

.. code-block:: bash

    $ python hexfilter -i log1 > log1.filtered
    $ python hexfilter -i log2 > log2.filtered
    $ vimdiff log1.filtered log2.filtered # Use preferred diff tool

log1.filtered might look like this:

::

    [0.066867] 00000060: 02 00 00 00 10 08 40 00 08 00 00 00              ......@.....

and, log2.filtered like this:

::

    [0.066791] 00000060: 02 00 00 00 10 08 40 00 08 00 00 00              ......@.....

Comparing these files with a diff tool will show a difference even if the
timing is nearly identical (the difference is only 76 us). Such a small
difference is not likely to impose a timing problem, so we would like to filter
out this and other dumps with similar (small) timing differences.

Adding a "-r 1000" argument to hexfilter will make it round each timestamp to
the nearest millisecond.

.. code-block:: bash

    $ python hexfilter -i log1 -r 1000 > log1.filtered
    $ python hexfilter -i log2 -r 1000 > log2.filtered
    $ vimdiff log1.filtered log2.filtered # Use preferred diff tool

log1.filtered:

::

    [0.067000] 00000060: 02 00 00 00 10 08 40 00 08 00 00 00              ......@.....

log2.filtered:

::

    [0.067000] 00000060: 02 00 00 00 10 08 40 00 08 00 00 00              ......@.....

Now the difference is gone and we can focus on the real timing issues.
The diff won't get spammed with irrelevant timing issues, so those that could
impose a real timing problem will clearly stand out.
