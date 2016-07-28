
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

    def __init__(self, skip_time_stamps = False):
        self.ts_regex = re.compile(ts_regex_pattern)
        self.dump_regex = re.compile(hex_dump_regex_pattern)
        self.skip_time_stamps = skip_time_stamps
        self.data_available = False

    def parse_line(self, line):
        """ Parses a line of the log file and tries to interpret the hex data.

        If no data could be retrieved (the line does not contain any valid
        hex data), False will be returned.

        If the line contains valid log data, the data will be read and stored
        internally. In this case, True will be returned.
        """
        if not self.skip_time_stamps:
            ts_match = self.ts_regex.match(line)
            if ts_match is None:
                return False

            self.ts = ts_match.group(1)

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
        returned
        """

        if not self.data_available:
            return None

        ljust_len = 0
        str = ''
        if not self.skip_time_stamps:
            str = '[{}] '.format(self.ts)
            ljust_len = len(str)

        str = '{}{}: {}'.format(str, self.dump_addr, self.dump_data)
        ljust_len += len(self.dump_addr) + 1 + max_num_hex_dump_values * 3 + 2
        str = str.ljust(ljust_len)
        str = '{}{}'.format(str, self.dump_data_ascii)
        self.data_available = False
        return str
