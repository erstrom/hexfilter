from hexfilter import HexFilterLinux

import argparse
import pdb
import traceback
import sys
import os


def load_options():
    global parsed_args
    parser = argparse.ArgumentParser(prog="hexfilter")

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
                             "converting all times tamps to delta times "
                             "(default behaviour)")
    parser.add_argument('-r', '--rounding', type=int, default=0,
                        help="Timestamp rounding value in us."
                             "This option is not effective when absolute "
                             "timestamps are used. "
                             "All delta times will be rounded to the "
                             "nearest rounding step.")
    parser.add_argument('-d', '--desc-str', nargs='+', type=str,
                        help="Description string(s) of the dumps."
                             "Only dumps containing a description string "
                             "matching any of the provided desc strings "
                             "will be filtered out."
                             "If no --desc-str option is given, no descripton "
                             "filtering will be performed.")
    parser.add_argument('-k', '--keep-desc-str', action="store_true",
                        help="Keep the description string of the dump in "
                             "the filtered output.")

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
                            log_has_timestamps=(not parsed_args.no_timestamps),
                            include_dump_desc_in_output=parsed_args.keep_desc_str)
        for line in infp:
            if hf.parse_line(line):
                result = hf.get_hex()
                outfp.write("%s\n" % (result))
    except:
        type, value, tb = sys.exc_info()
        traceback.print_exc()
        pdb.post_mortem(tb)

if __name__ == "__main__":
    main()
