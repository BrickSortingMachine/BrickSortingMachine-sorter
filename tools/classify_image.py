import os
import pathlib
import sys

# add robolab folder to python path
p = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(p)


import sorter.classification_service.classifier
import sorter.util.argument_parser

# parse command line arguments
parser = sorter.util.argument_parser.ArgumentParser(
    description="Rename file to sha1 key"
)
parser.add_argument("--fn", required=True)
args = parser.parse_args()


c = sorter.classification_service.classifier.Classifier(
    pathlib.Path("models\\2024-08-04_12-44-43_multi-view_abandoned-space.keras")
)

res = c.predict(args.fn)

print(res)
