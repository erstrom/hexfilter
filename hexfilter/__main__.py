from hexfilter import HexFilter

import argparse
import pdb
import traceback
import sys
import os

def load_options():
    global parsed_args
    parser = argparse.ArgumentParser(prog="hex_filter")

    parser.add_argument('-s','--skip-time-stamps', action="store_true",
                        help = "Skip all log time stamps when generating the "
                               "output.")
    parser.add_argument('-i','--input-file',
                        help = "Input (log) file to filter. If omitted, "
                               "stdin will be read")
    parser.add_argument('-o','--output-file',
                        help = "Filtered output file. If omitted, "
                               "the output will be written to stdout")

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
        hf = HexFilter(parsed_args.skip_time_stamps)
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
