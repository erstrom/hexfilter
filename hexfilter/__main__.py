from hexfilter import HexFilterLinux

import argparse
import pdb
import traceback
import sys
import os

description = \
    "hexfilter scans input (log) files for lines containing hex dumps.\n" \
    "When a line containing a hex dump is encountered, hexfilter will write it\n" \
    "to an output file or stdout (depending on input arguments, see below).\n\n" \
    "The current version of the tool only support linux kernel hex dumps, i.e.\n" \
    "dumps produced by the print_hex_dump* functions in the kernel.\n\n" \
    "The Linux kernel can be configured to add timestamps to all log messages.\n" \
    "It is recommended to have those timestamps enabled when using hexfilter\n" \
    "since it is capable of extracting timing information from the logs.\n\n" \
    "If the kernel logs does not contain any timestamps, arguments -n or\n" \
    "--no-timestamps must be used, otherwise the hex dump data can't be\n" \
    "interpreted.\n\n"

epilog = \
    "For full documentation, please visit:\n\n" \
    "http://hexfilter.readthedocs.io\n\n"


def load_options():
    global parsed_args
    parser = argparse.ArgumentParser(prog="hexfilter",
                                     description=description,
                                     epilog=epilog,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-i', '--input-file',
                        help="Input (log) file to filter. If omitted, "
                             "stdin will be read")
    parser.add_argument('-o', '--output-file',
                        help="Filtered output file. If omitted, "
                             "the output will be written to stdout")
    parser.add_argument('-n', '--no-timestamps', action="store_true",
                        help="Specifies whether or not the input file "
                             "contains time stamps. "
                             "If set, --skip-timestamps, --abs-timestamps "
                             "and --rounding will have no effect.")
    parser.add_argument('-s', '--skip-timestamps', action="store_true",
                        help="Skip all log timestamps when generating the "
                             "output.")
    parser.add_argument('-a', '--abs-timestamps', action="store_true",
                        help="Add absolute timestamps (keep log time "
                             "stamps as is) to the output instead of "
                             "converting all times tamps to delta times")
    parser.add_argument('-r', '--rounding', type=int, default=0,
                        help="Timestamp rounding value in us."
                             "This option is not effective when absolute "
                             "timestamps are used. "
                             "All delta times will be rounded to the "
                             "nearest rounding step.")
    parser.add_argument('-d', '--desc-str', nargs='+', type=str,
                        help="Description string(s) of the dumps. "
                             "Only dumps containing a description string "
                             "matching any of the provided desc strings "
                             "will be filtered out. "
                             "If no --desc-str option is given, no description "
                             "filtering will be performed.")
    parser.add_argument('-v', '--desc-str-invert', nargs='+', type=str,
                        help="Description string(s) of the dumps to be "
                             "excluded. Similar to --desc-str, but all "
                             "matching descriptions will be excluded from the "
                             "dump.")
    parser.add_argument('-k', '--keep-desc-str', action="store_true",
                        help="Keep the description string of the dump in "
                             "the filtered output.")
    parser.add_argument('-b', '--keep-non-hex-before', type=int, default=0,
                        metavar='N',
                        help="Keep N non hex dump lines from the input before "
                             "each valid hex dump. "
                             "These non hex dump lines will be added to the "
                             "filtered output before every burst of detected "
                             "hex dumps. ")
    parser.add_argument('--skip-ascii', action="store_true",
                        help="Don't include the ascii part of the hexdump in "
                             "the output.")

    parsed_args = parser.parse_args()


def main():
    global parsed_args
    load_options()

    try:
        if parsed_args.input_file:
            infp = open(parsed_args.input_file, "r")
        else:
            infp = sys.stdin
        if parsed_args.output_file:
            outfp = open(parsed_args.output_file, "w")
        else:
            outfp = sys.stdout
        hf = HexFilterLinux(skip_timestamps=parsed_args.skip_timestamps,
                            abs_timestamps=parsed_args.abs_timestamps,
                            timestamps_round_us=parsed_args.rounding,
                            dump_desc=parsed_args.desc_str,
                            dump_desc_invert=parsed_args.desc_str_invert,
                            log_has_timestamps=(not parsed_args.no_timestamps),
                            include_dump_desc_in_output=parsed_args.keep_desc_str,
                            keep_n_lines_before_each_dump=parsed_args.keep_non_hex_before,
                            remove_ascii_part=parsed_args.skip_ascii)
        for line in infp:
            if hf.parse_line(line):
                if parsed_args.keep_non_hex_before > 0:
                    before = hf.get_lines_before_hex()
                    if before:
                        outfp.write("%s" % (before))
                result = hf.get_hex()
                outfp.write("%s\n" % (result))

    except:
        type, value, tb = sys.exc_info()
        traceback.print_exc()
        pdb.post_mortem(tb)

if __name__ == "__main__":
    main()
