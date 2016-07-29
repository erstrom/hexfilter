
import re
import string

# Linux kernel dump_hex regex'es.
# Sample string:
# [    7.852404] sdio wr 00000000: 06 00 00 00 44 12 00 00                          ....D...
# Timestamp regex:
ts_regex_pattern = '.*\[(\s*\d+\.\d+)\]\s+'
# linux hex_dump log regex
hex_dump_regex_pattern = '.+([0-9a-f]{8}):\s(.+)'

# Linux hex_dump only uses lower case (a-f) for all hex values
valid_hex_data_chars = '0123456789abcdef '
valid_hex_data_ascii_chars = string.digits + string.ascii_letters + \
                             string.punctuation

# Linux hex_dump will contain at most 16 hex values in one line
max_num_hex_dump_values = 16

class HexFilter:

    def __init__(self, skip_timestamps = False, abs_timestamps = False,
                 timestamps_round_us = 0):
        """ HexFilter constructor

        Keyword arguments:
        skip_timestamps -- (bool) Don't add timestamps to the output
                            (default False)
        abs_timestamps  -- (bool) Add absolute timestamps to the output
                            instead of delta times. This argument will not
                            have any effect if skip_timestamps is True
                            (default False).
        timestamps_round_us -- (int) Timestamp rounding factor in microseconds.
                                All timestamps will be rounded to the nearest
                                timestamps_round_us microsecond
        """
        self.ts_regex = re.compile(ts_regex_pattern)
        self.dump_regex = re.compile(hex_dump_regex_pattern)
        self.skip_timestamps = skip_timestamps
        self.abs_timestamps = abs_timestamps
        self.timestamps_round_us = timestamps_round_us
        self.prev_ts = None
        self.data_available = False

    def __update_ts(self, line):
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

    def parse_line(self, line):
        """ Parses a line of the log file and tries to interpret the hex data.

        If no data could be retrieved (the line does not contain any valid
        hex data), False will be returned.

        If the line contains valid log data, the data will be read and stored
        internally. In this case, True will be returned.
        """
        if not self.skip_timestamps:
            if not self.__update_ts(line):
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
        if not all(c in valid_hex_data_chars for c in self.dump_data):
            return False

        self.dump_data_ascii = dump_data_a[1]
        self.dump_data_ascii = self.dump_data_ascii.lstrip(' ')
        if not all(c in valid_hex_data_ascii_chars for c in self.dump_data_ascii):
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
        ljust_len += len(self.dump_addr) + 1 + max_num_hex_dump_values * 3 + 2
        str = str.ljust(ljust_len)
        str = '{}{}'.format(str, self.dump_data_ascii)
        self.data_available = False
        return str
