
import re
import string

from abc import ABCMeta, abstractmethod

##
# Linux definitions:

# Linux kernel dump_hex regex'es.
# Sample string:
# [    7.852404] sdio wr 00000000: 06 00 00 00 44 12 00 00                          ....D...
# Timestamp regex:
linux_ts_regex_pattern = '.*\[(\s*\d+\.\d+)\]\s+'
# linux hex_dump log regex
linux_hex_dump_regex_pattern = '.+([0-9a-f]{8}):\s(.+)'

# Linux hex_dump uses lower case (a-f) for all hex values
linux_valid_hex_data_chars = '0123456789abcdef '

##
# Generic/default definitions (applicable to most hex dump formats):

default_hex_dump_regex_pattern = '.+([0-9a-fA-F]{8}):\s(.+)'
default_valid_hex_data_chars = string.hexdigits + ' '
default_valid_ascii_chars = string.digits + string.ascii_letters + \
                            string.punctuation
default_max_num_hex_dump_values = 16


##
# HexFilter abstract base class
class HexFilter:
    __metaclass__ = ABCMeta

    def __init__(self,
                 ts_regex_pattern=None,
                 hex_dump_regex_pattern=default_hex_dump_regex_pattern,
                 valid_hex_data_chars=default_valid_hex_data_chars,
                 valid_ascii_chars=default_valid_ascii_chars,
                 max_num_hex_dump_values=default_max_num_hex_dump_values,
                 skip_timestamps=False,
                 abs_timestamps=False,
                 timestamps_round_us=0):
        """ HexFilter constructor

        This is the HexFilter base class constructor used by inheriting
        classes.

        Keyword arguments:
        ts_regex_pattern        -- (string) Regex pattern for time stamps
        hex_dump_regex_pattern  -- (string) Regex pattern for hex dumps
        valid_hex_data_chars    -- (string) Valid hex digits + separator
        valid_ascii_chars       -- (string) Valid chars in the ascii part of the
                                   dump
        max_num_hex_dump_values -- (int) Maximum number of hex values in a dump
                                   line
        skip_timestamps         -- (bool) Don't add timestamps to the output
                                   (default False)
        abs_timestamps          -- (bool) Add absolute timestamps to the output
                                   instead of delta times. This argument will not
                                   have any effect if skip_timestamps is True
                                   (default False)
        timestamps_round_us     -- (int) Timestamp rounding factor in microseconds.
                                   All timestamps will be rounded to the nearest
                                   timestamps_round_us microsecond
        """
        self.valid_hex_data_chars = valid_hex_data_chars
        self.valid_ascii_chars = valid_ascii_chars
        self.max_num_hex_dump_values = max_num_hex_dump_values

        if ts_regex_pattern:
            self.ts_regex = re.compile(ts_regex_pattern)
        else:
            # A timestamp regex is not mandatory
            self.ts_regex = None
        if hex_dump_regex_pattern:
            self.dump_regex = re.compile(hex_dump_regex_pattern)
        else:
            # We must have a hex_dump_regex_pattern, so we will use a default
            # if no pattern was provided by the caller.
            self.dump_regex = re.compile(default_hex_dump_regex_pattern)
        self.skip_timestamps = skip_timestamps
        self.abs_timestamps = abs_timestamps
        self.timestamps_round_us = timestamps_round_us
        self.prev_ts = None
        self.data_available = False

    def update_ts(self, line):
        """ Protected/private method used by inheriting classes.

        Reads the timestamp associated with the hex dump log and
        converts the timestamp into a delta time (unless abs_timestamps
        was used with the constructor).

        If timestamps_round_us > 0, the delta time will be rounded to the
        nearest timestamps_round_us microsecond.
        """
        if not self.ts_regex:
            return False

        ts_match = self.ts_regex.match(line)
        if ts_match is None:
            return False

        self.ts = ts_match.group(1)
        if self.prev_ts is None:
            self.ts_diff = 0.0
        else:
            self.ts_diff = float(self.ts) - float(self.prev_ts)
        self.prev_ts = self.ts

        if self.ts_diff > 0 and self.timestamps_round_us > 0:
            div_floor = (self.ts_diff * 1E6) // self.timestamps_round_us
            ts_diff_floor = self.timestamps_round_us / 1E6 * div_floor
            ts_diff_modulo_us = (self.ts_diff - ts_diff_floor) * 1E6
            if (ts_diff_modulo_us - self.timestamps_round_us / 2) < 0:
                self.ts_diff = ts_diff_floor
            else:
                self.ts_diff = ts_diff_floor + self.timestamps_round_us / 1E6

        return True

    @abstractmethod
    def parse_line(self, line):
        """ Parses a line of the log file and tries to interpret the hex data.

        If no data could be retrieved (the line does not contain any valid
        hex data), False will be returned.

        If the line contains valid log data, the data will be read and stored
        internally. In this case, True will be returned.
        """
        pass

    @abstractmethod
    def get_hex(self):
        """ Returnes the most recent hex data string or None if no hex data
        string is available. Not available could mean that no valid hex string
        has been read yet or the that the most recent string has already been
        returned.

        The returned string will be formatted according to the setup arguments
        of the constructor.
        """
        pass


##
# HexFilterLinux
class HexFilterLinux(HexFilter):

    """ HexFilter class for filtering linux print_hex_data dumps
    from a linux kernel log.
    """
    def __init__(self, skip_timestamps=False, abs_timestamps=False,
                 timestamps_round_us=0):
        HexFilter.__init__(self,
                           ts_regex_pattern=linux_ts_regex_pattern,
                           hex_dump_regex_pattern=linux_hex_dump_regex_pattern,
                           valid_hex_data_chars=linux_valid_hex_data_chars,
                           skip_timestamps=skip_timestamps,
                           abs_timestamps=abs_timestamps,
                           timestamps_round_us=timestamps_round_us)

    def parse_line(self, line):
        """ Parses a line of the log file and tries to interpret the hex data.

        If no data could be retrieved (the line does not contain any valid
        hex data), False will be returned.

        If the line contains valid log data, the data will be read and stored
        internally. In this case, True will be returned.
        """

        if not self.skip_timestamps and self.ts_regex:
            if not self.update_ts(line):
                return False

        dump_match = self.dump_regex.match(line)
        if dump_match is None:
            return False

        self.dump_addr = dump_match.group(1)
        dump_data = dump_match.group(2)
        # Split up dump data into hex part and ASCII part
        # A linux kernel hex_dump will always have at least two
        # spaces between the hex part and the ASCII part.
        dump_data_a = dump_data.split('  ', 1)
        if len(dump_data_a) != 2:
            return False

        self.dump_data = dump_data_a[0]
        if not all(c in self.valid_hex_data_chars for c in self.dump_data):
            return False

        self.dump_data_ascii = dump_data_a[1]
        self.dump_data_ascii = self.dump_data_ascii.lstrip(' ')
        if not all(c in self.valid_ascii_chars for c in self.dump_data_ascii):
            return False

        self.data_available = True
        return True

    def get_hex(self):
        """ Returnes the most recent hex data string or None if no hex data
        string is available. Not available could mean that no valid hex string
        has been read yet or the that the most recent string has already been
        returned.

        The returned string will be formatted according to the setup arguments
        of the constructor.
        """

        if not self.data_available:
            return None

        ljust_len = 0
        str = ''
        if not self.skip_timestamps:
            if self.abs_timestamps:
                str = '[{:.6f}] '.format(self.ts)
            else:
                str = '[{:.6f}] '.format(self.ts_diff)
            ljust_len = len(str)

        str = '{}{}: {}'.format(str, self.dump_addr, self.dump_data)
        ljust_len += len(self.dump_addr) + 1 + self.max_num_hex_dump_values * 3 + 2
        str = str.ljust(ljust_len)
        str = '{}{}'.format(str, self.dump_data_ascii)
        self.data_available = False
        return str
