import argparse
import sys


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write("Error: %s\n" % message)
        self.print_help()
        sys.exit(2)
