import logging
import os
import pathlib
import sys
import urllib.request
import zipfile

# add robolab folder to python path
p = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(p)

import sorter.util.argument_parser
import sorter.util.file_hash

file_list = [
    # currently deactivated until new test recordings are uploaded
    # "rec_2022-04-21_12-42-15_752a5cff2028011843b4b39f7a33769cce617499.zip",
    # "rec_2022-04-21_12-42-30_e97badf034f8bbf24bf6956dac6c405abc55d7be.zip",
    # "rec_2022-04-21_12-53-11_5ad7341458687920d53e497dbd8184c6202e0abb.zip",
    # "rec_2023-08-09_21-38-43_0f5ca2e91a5d6718f4a17a0d4b1346553439c350.zip",
]

if __name__ == "__main__":
    # configure logger
    logFormatter = logging.Formatter(
        "%(levelname)-7.7s %(asctime)s %(filename)s:%(lineno)d %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.DEBUG)

    # adding a console loger at info loglevel
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    consoleHandler.setLevel(logging.INFO)
    rootLogger.addHandler(consoleHandler)

    # parse command line arguments
    parser = sorter.util.argument_parser.ArgumentParser(
        description="Download Test Data"
    )
    parser.add_argument("--name", required=False)
    args = parser.parse_args()

    # data folder
    data_path = pathlib.Path(__file__).parents[1].resolve() / "data"
    if not data_path.exists():
        raise Exception(f"Data folder {str(data_path)} does not exist.")

    # explicit name
    if args.name is not None:
        file_list = [args.name]

    logging.info("Will download the following files:")
    for n in file_list:
        logging.info(f"  {n}")

    count_downloaded = 0
    count_exist = 0
    logging.info(" ")
    logging.info("Starting file download ...")
    logging.info(" ")
    for fn in file_list:
        file_path = data_path / fn
        logging.info(f"Package: {str(fn)}")
        if not file_path.exists():
            # download, file does not exist yet
            url = (
                "https://github.com/BrickSortingMachine/sorter/releases/download/BaseRelease/"
                + fn
            )

            logging.info(f"Downloading {url} ...")
            urllib.request.urlretrieve(url, str(file_path))
            count_downloaded += 1
        else:
            # file already exists
            logging.info("File already exists")
            count_exist += 1

        # hash from filename
        # example: frame_000000_8b0df9a0cc0790c312619533dd78622dd94aa83c.png
        specified_hash = fn.split("_")[-1].split(".")[0]

        # hash from file content
        actual_hash = sorter.util.file_hash.file_hash(str(file_path))
        if specified_hash == actual_hash:
            logging.info("Hash verified to be correct.")
            pass
        else:
            logging.error(" ")
            logging.error(" ")
            logging.error("!!!!!!!!!!!!!!!!")
            logging.error("! Invalid hash !")
            logging.error("!!!!!!!!!!!!!!!!")
            sys.exit(1)

        # unpack
        with zipfile.ZipFile(str(file_path), "r") as zip_ref:
            all_files_exist = True
            c_files = 0
            for member in zip_ref.namelist():
                target_path = os.path.join(str(data_path), member)
                if not os.path.exists(target_path):
                    all_files_exist = False
                else:
                    c_files += 1
            if all_files_exist:
                logging.info(f"All {c_files} files already exist - will not unpack.")
            else:
                logging.info("Unpacking ...")
                zip_ref.extractall(str(data_path))
                logging.info("done.")

        logging.info(" ")

    logging.info(" ")
    logging.info("All files verified successfully.")
    logging.info("Downloaded: %d" % count_downloaded)
    logging.info("Existed:    %d" % count_exist)
