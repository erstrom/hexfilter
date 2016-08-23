
import re
import string
# Check if we are running Python 2 or Python 3
try:
    unicode = unicode
except NameError:
    # 'unicode' is undefined, must be Python 3
    str = str
    unicode = str
    bytes = bytes
    basestring = (str, bytes)
else:
    # 'unicode' exists, must be Python 2
    str = str
    unicode = unicode
    bytes = str
    basestring = basestring

from abc import ABCMeta, abstractmethod
from collections import deque

##
# Linux definitions:

# Linux kernel dump_hex regex'es.
# Sample string with time stamp:
# [    7.852404] sdio wr 00000000: 06 00 00 00 44 12 00 00                          ....D...
# Without timestamp:
# sdio wr 00000000: 06 00 00 00 44 12 00 00                          ....D...
linux_hex_dump_regex_pattern = '(.+)([0-9a-f]{8}):\s(.+)'
linux_hex_dump_ts_regex_pattern = '.*\[(\s*\d+\.\d+)\]\s+(.+)([0-9a-f]{8}):\s(.+)'

# Linux hex_dump uses lower case (a-f) for all hex values
linux_valid_hex_data_chars = '0123456789abcdef '

##
# Generic/default definitions (applicable to most hex dump formats):

default_hex_dump_regex_pattern = '.+([0-9a-fA-F]{8}):\s(.+)'
default_valid_hex_data_chars = string.hexdigits + ' '
default_valid_ascii_chars = string.digits + string.ascii_letters + \
                            string.punctuation + ' '
default_max_num_hex_dump_values = 16


##
# HexFilter abstract base class
class HexFilter:
    __metaclass__ = ABCMeta

    def __init__(self,
                 hex_dump_regex_pattern=default_hex_dump_regex_pattern,
                 valid_hex_data_chars=default_valid_hex_data_chars,
                 valid_ascii_chars=default_valid_ascii_chars,
                 max_num_hex_dump_values=default_max_num_hex_dump_values,
                 skip_timestamps=False,
                 abs_timestamps=False,
                 timestamps_round_us=0,
                 keep_n_lines_before_each_dump=0):
        """ HexFilter constructor

        This is the HexFilter base class constructor used by inheriting
        classes.

        Keyword arguments:
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
        keep_n_lines_before_each_dump -- (int) Number of before-dump-lines to
                                   store internally by parse_line.
                                   When the number of stored lines has reached
                                   this limit, older lines will be rotated out
                                   before new lines are inserted
                                   (default 0)
        """
        self.valid_hex_data_chars = valid_hex_data_chars
        self.valid_ascii_chars = valid_ascii_chars
        self.max_num_hex_dump_values = max_num_hex_dump_values

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

        self.keep_n_lines_before_each_dump = keep_n_lines_before_each_dump
        if self.keep_n_lines_before_each_dump > 0:
            self.before_lines = deque()
        else:
            self.before_lines = None

    def update_ts(self, ts):
        """ Protected/private method used by inheriting classes.

        Reads the timestamp associated with the hex dump log and
        converts the timestamp into a delta time (unless abs_timestamps
        was used with the constructor).

        If timestamps_round_us > 0, the delta time will be rounded to the
        nearest timestamps_round_us microsecond.
        """

        self.ts = ts
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
        """ Returns the most recent hex data string or None if no hex data
        string is available. Not available could mean that no valid hex string
        has been read yet or the that the most recent string has already been
        returned.

        The returned string will be formatted according to the setup arguments
        of the constructor.
        """
        pass

    @abstractmethod
    def get_lines_before_hex(self):
        """ Returns the most recent non hex data string that was encountered
        before the most recent hex dump. If no non hex data strings has been
        encountered, None will be returned.

        The hex data string will contain a number of lines set by the
        keep_n_lines_before_each_dump argument to the constructor (at most).

        After the string containing the lines has been returned, the
        internal storage will be cleared. Thus, subsequent calls to this
        function will return None until new non hex lines have been encountered.
        """
        pass


##
# HexFilterLinux
class HexFilterLinux(HexFilter):

    """ HexFilter class for filtering linux print_hex_data dumps
    from a linux kernel log.
    """
    def __init__(self, skip_timestamps=False, abs_timestamps=False,
                 timestamps_round_us=0, log_has_timestamps=True,
                 dump_desc=None, dump_desc_invert=None,
                 include_dump_desc_in_output=False,
                 keep_n_lines_before_each_dump=0):
        """ HexFilterLinux constructor

        Constructor for linux kernel log parser .

        Keyword arguments:
        skip_timestamps         -- (bool) Don't add timestamps to the output
                                   (default False)
        abs_timestamps          -- (bool) Add absolute timestamps to the output
                                   instead of delta times. This argument will not
                                   have any effect if skip_timestamps is True
                                   (default False)
        timestamps_round_us     -- (int) Timestamp rounding factor in microseconds.
                                   All timestamps will be rounded to the nearest
                                   timestamps_round_us microsecond
                                   (default 0)
        log_has_timestamps      -- (bool) The log files has printk timestamps, i.e,
                                   the kernel was built with CONFIG_PRINTK_TIME
                                   (default True)
        dump_desc               -- (string or array) Description string(s) for each dump.
                                   If set, only dumps containing the description(s)
                                   will be filtered out.
                                   If dump_desc is an array (of strings), each string
                                   in the array will be checked against the description
                                   string in the dump. If any string matches, the dump
                                   will be considered valid.
                                   (default None)
        dump_desc_invert        -- (string or array) Same as dump_desc but matching
                                   strings will be removed from the output.
        include_dump_desc_in_output --(bool) Include the dump description string in the
                                   produced output
                                   (default False)
        """
        if log_has_timestamps:
            regex_pattern = linux_hex_dump_ts_regex_pattern
        else:
            regex_pattern = linux_hex_dump_regex_pattern

        HexFilter.__init__(self,
                           hex_dump_regex_pattern=regex_pattern,
                           valid_hex_data_chars=linux_valid_hex_data_chars,
                           skip_timestamps=skip_timestamps,
                           abs_timestamps=abs_timestamps,
                           timestamps_round_us=timestamps_round_us,
                           keep_n_lines_before_each_dump=keep_n_lines_before_each_dump)

        self.log_has_timestamps = log_has_timestamps
        self.include_dump_desc_in_output = include_dump_desc_in_output

        if dump_desc:
            self.dump_desc_regexes = []
            if isinstance(dump_desc, basestring):
                self.dump_desc_regexes.append(re.compile(dump_desc))
            elif isinstance(dump_desc, (list, tuple)):
                for item in dump_desc:
                    self.dump_desc_regexes.append(re.compile(item))
        else:
            self.dump_desc_regexes = None

        if dump_desc_invert:
            self.dump_desc_invert_regexes = []
            if isinstance(dump_desc_invert, basestring):
                self.dump_desc_invert_regexes.append(re.compile(dump_desc_invert))
            elif isinstance(dump_desc_invert, (list, tuple)):
                for item in dump_desc_invert:
                    self.dump_desc_invert_regexes.append(re.compile(item))
        else:
            self.dump_desc_invert_regexes = None

    def __store_non_hex_line(self, line, lines, limit):

        if limit == len(lines):
            # Shift out the oldest stored line and make place
            # for a new line
            lines.rotate(1)
            lines.popleft()

        # Append the new line before the old ones
        lines.appendleft(line)

    def __handle_non_match(self, line):

        if self.keep_n_lines_before_each_dump > 0:
            self.__store_non_hex_line(line, self.before_lines,
                                      self.keep_n_lines_before_each_dump)

    def __match_dump_desc(self, regexes):

        matching_str_found = False

        for regex in regexes:
            desc_match = regex.match(self.cur_dump_desc)
            if desc_match:
                matching_str_found = True
                break

        return matching_str_found

    def parse_line(self, line):
        """ Parses a line of the log file and tries to interpret the hex data.

        If no data could be retrieved (the line does not contain any valid
        hex data), False will be returned.

        If the line contains valid log data, the data will be read and stored
        internally. In this case, True will be returned.
        """

        dump_match = self.dump_regex.match(line)
        if dump_match is None:
            self.__handle_non_match(line)
            return False

        match_idx = 1
        if self.log_has_timestamps:
            log_ts = dump_match.group(match_idx)
            match_idx += 1
            if not self.skip_timestamps and not self.update_ts(log_ts):
                return False

        self.cur_dump_desc = dump_match.group(match_idx)
        match_idx += 1

        if self.dump_desc_regexes:
            if not self.__match_dump_desc(self.dump_desc_regexes):
                return False

        if self.dump_desc_invert_regexes:
            if self.__match_dump_desc(self.dump_desc_invert_regexes):
                return False

        self.dump_addr = dump_match.group(match_idx)
        match_idx += 1
        dump_data = dump_match.group(match_idx)
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
        """ Returns the most recent hex data string or None if no hex data
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
        if self.log_has_timestamps and not self.skip_timestamps:
            if self.abs_timestamps:
                str = '[{:.6f}] '.format(self.ts)
            else:
                str = '[{:.6f}] '.format(self.ts_diff)
            ljust_len = len(str)

        if self.include_dump_desc_in_output and self.cur_dump_desc:
            str = '{}{} '.format(str, self.cur_dump_desc)
            ljust_len = len(str)

        str = '{}{}: {}'.format(str, self.dump_addr, self.dump_data)
        ljust_len += len(self.dump_addr) + 1 + self.max_num_hex_dump_values * 3 + 2
        str = str.ljust(ljust_len)
        str = '{}{}'.format(str, self.dump_data_ascii)
        self.data_available = False
        return str

    def __get_non_hex_lines(self, lines):

        if lines is None or len(lines) == 0:
            return None

        str = ''
        for line in reversed(lines):
            str = '{}{}'.format(str, line)

        lines.clear()

        return str

    def get_lines_before_hex(self):

        return self.__get_non_hex_lines(self.before_lines)
