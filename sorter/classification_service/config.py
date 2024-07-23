import pathlib

# local
data_dir_path = pathlib.Path(__file__).parents[2] / "data"  # fast working dir

# incoming
incoming_data_known_class_train_dir_path = (
    data_dir_path / "incoming_data_known_class_train"
)
incoming_data_known_class_test_dir_path = (
    data_dir_path / "incoming_data_known_class_test"
)
trash_dir_path = data_dir_path / "trash"
inconsistent_dir_path = data_dir_path / "incoming_data_inconsistent"
