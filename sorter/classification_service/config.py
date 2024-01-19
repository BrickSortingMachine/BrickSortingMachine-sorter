import logging
import pathlib

# check colab
try:
    from IPython import get_ipython

    shell = get_ipython().__class__.__name__
    colab_mode = True
except Exception:
    colab_mode = False
logging.info(f"Colab Mode: {colab_mode}")

if not colab_mode:
    # local
    data_dir_path = pathlib.Path(__file__).parents[2] / "data"  # fast working dir
else:
    # colab
    data_dir_path = pathlib.Path("/content/data")  # fast working dir
    data_zip_dir_path = pathlib.Path(
        "/content/drive/MyDrive/sorter/data"
    )  # folder with zip files
    data_cutout_zip_dir_path = data_zip_dir_path / "training_data_cutout"
    data_unit_test_cutout_zip_dir_path = data_zip_dir_path / "unit_test_data_cutout"

# incoming
incoming_data_known_class_train_dir_path = (
    data_dir_path / "incoming_data_known_class_train"
)
incoming_data_known_class_test_dir_path = (
    data_dir_path / "incoming_data_known_class_test"
)
trash_dir_path = data_dir_path / "trash"
inconsistent_dir_path = data_dir_path / "incoming_data_inconsistent"

# storage
training_data_dir_path = data_dir_path / "training_data"
unit_test_data_dir_path = data_dir_path / "unit_test_data"

# cutouts
training_data_cutout_dir_path = data_dir_path / "training_data_cutout"
unit_test_data_cutout_dir_path = data_dir_path / "unit_test_data_cutout"

# grouped cutouts
tf_training_dir_path = data_dir_path / "training_data_tf"
tf_training_low_dir_path = data_dir_path / "training_data_tf_low"
tf_training_high_dir_path = data_dir_path / "training_data_tf_high"
tf_cross_val_dir_path = data_dir_path / "training_data_cross_val_tf"
tf_unit_test_dir_path = data_dir_path / "unit_test_data_tf"
tf_unit_test_low_dir_path = data_dir_path / "unit_test_data_tf_low"
tf_unit_test_high_dir_path = data_dir_path / "unit_test_data_tf_high"
