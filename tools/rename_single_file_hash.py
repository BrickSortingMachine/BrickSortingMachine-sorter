import logging
import os
import pathlib
import sys

# add robolab folder to python path
p = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(p)

import sorter.util.argument_parser
import sorter.util.file_hash

if __name__ == "__main__":
    # configure logger
    logFormatter = logging.Formatter(
        "%(levelname)-7.7s %(asctime)s %(filename)s:%(lineno)d %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.DEBUG)

    # adding a console logger at info loglevel
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    consoleHandler.setLevel(logging.INFO)
    rootLogger.addHandler(consoleHandler)

    # parse command line arguments
    parser = sorter.util.argument_parser.ArgumentParser(
        description="Rename file to sha1 key"
    )
    parser.add_argument("--name", required=True)
    args = parser.parse_args()

    src_fp = pathlib.Path(args.name).resolve()
    logging.info(f"Source-File: {str(src_fp)}")
    if not src_fp.exists():
        logging.error("File does not exist.")
        sys.exit(1)

    # compute hash
    h = sorter.util.file_hash.file_hash(str(src_fp))

    dst_fp = src_fp.parents[0] / (src_fp.stem + "_" + h + src_fp.suffix)
    logging.info(f"Renaming {str(src_fp)} -> {str(dst_fp)}")
    os.rename(str(src_fp), str(dst_fp))
