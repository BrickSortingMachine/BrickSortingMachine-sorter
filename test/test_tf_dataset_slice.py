import logging
import unittest

import test_helpers

# run only if tensorflow available
tensorflow_available = False
try:
    import tensorflow as tf

    tensorflow_available = True
except ImportError:
    pass

if tensorflow_available:

    def list_from_ds(ds):
        return list(ds.as_numpy_iterator())

    def dataset_slice(dataset, start_index, count):
        tmp = dataset.skip(start_index)
        return tmp.take(count)


class TFDatasetSlice(unittest.TestCase, test_helpers.BaseTest):
    def test_general(self):
        self.setup_logging()

        if not tensorflow_available:
            logging.warning("Tensorflow not available - test not run.")
            return

        ds = tf.data.Dataset.range(10)
        print(list_from_ds(ds))
        self.assertEqual([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], list_from_ds(ds))

        b = dataset_slice(ds, 2, 3)
        print(list_from_ds(b))
        self.assertEqual([2, 3, 4], list_from_ds(b))
