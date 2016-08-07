.. hexfilter documentation master file, created by
   sphinx-quickstart on Sun Jul 31 07:19:41 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to hexfilter's documentation!
=====================================

hexfilter is a tool for filtering out hex dumps from log files.
The current version supports filtering of hex dumps obtained from the
print_hex_dump* functions in the linux kernel.

The purpose of the tool is to extract hex dumps from a log file
and write those dumps into another file using a common format.
The produced output can be compared with other outputs using a diff tool
(such as beyond compare, winmerge, meld etc.)

* GitHub: https://github.com/erstrom/hexfilter

Features
--------

- Support for extracting hex dumps produced by linux print_hex_dump
- Support for timestamp conversion/rounding of the hex dump logs in order to ease comparison
- Support for regex (regular expression) based filtering


Installing
----------

.. code-block:: bash

    $ git clone https://github.com/erstrom/hexfilter.git
    $ cd hexfilter
    $ sudo python setup.py install


Tool usage
----------

Run the tool with --help argument to list available options.

Perhaps the best way to explain how to use the tool is with a
couple of examples.

Example 1
^^^^^^^^^

Let's assume you have two drivers (running on two different machines) producing
log data containing hex dumps.

Below is an extract from driver A (extracted from a syslog file,
hence the extra syslog header before the kernel timestamp):

::

    Jul 15 17:25:56 xenial kernel: [272190.595082] SDIO TX 00000060: 02 00 00 00 10 08 40 00 08 00 00 00              ......@.....

And here is an extract from driver B:

::

    [  410.085422] sdio wr 00000060: 02 00 00 00 10 08 40 00 08 00 00 00              ......@.....

You would like to verify that the different drivers transmit the same data on
the SDIO interface.

Comparing the log files with a diff tool without any filtering would result in
a lot of differences even though the actual hex data is the same.

The actual filtering looks like this (assuming the hexfilter install dir is in PATH):

.. code-block:: bash

    $ hexfilter -i log1 -s > log1.filtered
    $ hexfilter -i log2 -s > log2.filtered
    $ vimdiff log1.filtered log2.filtered # Use preferred diff tool

Since hexfilter was invoked with the -s option, all timestamps were removed.
The filtered data in the above example would look like this for both log files:

::

    00000060: 02 00 00 00 10 08 40 00 08 00 00 00              ......@.....

The above result will make the diff tool not show any differences.
Only when the hex dump data differs, will it be detected by the diff tool.
This will make it a lot easier to spot "real" differences in the data.

Example 2: Timing
^^^^^^^^^^^^^^^^^

Sometimes it is useful to compare the timing of different driver
implementations as well as the hex data
(when was the command/message in the hex dump issued?).

Let's assume there are two driver implementations that issues
exactly the same commands (hex dumps are identical), but one of them works 
while the other doesn't.

The most likely cause in this case is timing. Perhaps the target hardware is
timing out before a certain command is issued?

If the -s (or --skip-timestamps) option is omitted, hexfilter will read the
timestamps from the input file (assuming there are any) and convert them into
delta times that will be written to the output together with the hex dump.

The delta times are the time difference between the hex dumps.

.. IMPORTANT::
    In order to analyze timing, the kernel logs must contain timestamps.
    This can be achieved in different ways.
    Kernel timestamps can be enabled at build time by enabling CONFIG_PRINTK_TIME
    in the kernel configuration 

    __or__

    at run time with the below command:
    echo 1 > /sys/module/printk/parameters/time

    __or__

    by adding the following command to the kernel command line: 
    printk.time=1


Even if two drivers have more or less exactly the same timing, there will most
likely still be a small deviation between timestamps in the log. The linux
kernel printk timestamps have microsecond resolution, so most likely the last
decimals will be slightly different every time the driver code is executed.

In order to mitigate this problem, hexfilter can be invoked with the -r
(or --rounding) option. This will make the timestamp rounded to the nearest
rounding step specified by the option. The option takes a microsecond argument.

Let's take the same hex dumps as in Example 1 but without the -s option:

.. code-block:: bash

    $ hexfilter -i log1 > log1.filtered
    $ hexfilter -i log2 > log2.filtered
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

Example 3: Filtering out specific hex dumps
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Below is one of the hex dumps used in the previous example:

::

    [  410.085422] sdio wr 00000060: 02 00 00 00 10 08 40 00 08 00 00 00              ......@.....

Notice the dump description string added immediately before the 
address/offset chunk. In this particular case the string is "sdio wr"
since the data was dumped from an SDIO driver. 

It is good practice to add such a description in the call to print_hex_dump
when writing linux drivers since it is much easier to see what kind of dump
we are dealing with.

"sdio wr" means sdio write, so the above data is TX data.
The sdio RX dumps for this particular driver will have the dump description
strings set to "sdio rd" (sdio read).

When extractig hex dumps from a log it is sometimes useful to filter the 
data based on the description string. Lets assume we wan't to compare the TX
data from two drivers. We would then want to filter out all dumps containing
"sdio wr"

hexfilter can be invoked with the -d (or --desc-str) option in order to achive
this.

Like this:

.. code-block:: bash

    $ hexfilter -i log1 -d "SDIO TX" > log1.filtered
    $ hexfilter -i log2 -d "sdio wr" > log2.filtered
    $ vimdiff log1.filtered log2.filtered # Use preferred diff tool

The above example will only filter out TX dumps

The argument to the -d option is treated as a regular expression and
must conform to the python re module regex syntax.

The -d option takes an arbitary number of string arguments (each will
be compiled into a regex). If the dump description matches any of the
arguments, the hex dump will be included in the output.

The below examples will all produce the same output:

.. code-block:: bash

    $ hexfilter -i log2 -d "sdio wr" "sdio rd" > log2.filtered1
    $ hexfilter -i log2 -d "sdio\swr" "sdio\srd" > log2.filtered2
    $ hexfilter -i log2 -d "sdio wr|sdio rd" > log2.filtered3

If the dump description string in the log contains any of the 
special regex characters, they must be escaped with a backslash: "\":

.. code-block:: bash

    # Below call will filter out dumps containing the string:
    # "sdio wr|sdio rd"
    # and not dumps containing the strings
    # "sdio wr" or "sdio rd"
    $ hexfilter -i log2 -d "sdio wr\|sdio rd" > log1.filtered1

Example 4: Logs without timestamps
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If the kernel log does not contain timestamps, hexfilter must be
invoked with the -n (or --no-timestamps) option.
If not, the internal regex matching will not be able to match
any input lines since it expects the timestamp to be present.

.. IMPORTANT::

    If hexfilter is used with the -n option when filtering logs
    containing timestamps, the description string filtering will
    not work as expected. The reason is that the timestamp will
    be included in the parsed dump description string and hence,
    if -d is used with simple strings like "sdio rd", there won't
    be any regex match.

Filter a log without timestamps:

.. code-block:: bash

    $ hexfilter -n -i log2 -d "sdio wr" "sdio rd" > log1.filtered1

Filter a log containing timestamps with the -n option:

.. code-block:: bash

    $ hexfilter -n -i log2 -d ".*sdio wr" ".*sdio rd" > log1.filtered1

Notice the ".*" used in both arguments to the -d option.
This is necessary in order to have a regex match.

.. toctree::
   :maxdepth: 2



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
