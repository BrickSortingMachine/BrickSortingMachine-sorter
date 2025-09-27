import json
import logging
import pathlib

import cv2

import sorter.classification_service.classification_result
import sorter.classification_service.crop_image
import sorter.classification_service.white_balance
import sorter.util.file_hash


class InvalidImageError(Exception):
    pass


class Classifier:
    def __init__(self, model_fp):
        import tensorflow as tf

        # softmax convert logits to probabilities
        # https://developers.google.com/machine-learning/glossary#logits
        # only .keras tested currently
        assert model_fp.suffix == ".keras"

        logging.info(f"Loading model {model_fp} ...")
        model = tf.keras.models.load_model(model_fp, compile=False)

        # add softmax layer -> output probabilities
        inputs = model.input
        outputs = tf.keras.layers.Softmax()(
            model.output[0]
        )  # Access the tensor directly
        self.probability_model = tf.keras.Model(inputs=inputs, outputs=outputs)

        # json
        json_fp = str(pathlib.Path(model_fp).with_suffix(".json"))
        with open(json_fp) as json_file:
            json_data = json.load(json_file)

        # verify hash
        hash = sorter.util.file_hash.file_hash(model_fp)
        if hash != json_data["model_hash"]:
            raise Exception(
                f"Model hash does not qual hash in json file (file hash: {hash})"
            )

        self.class_list = json_data["label_name_list"]

    def predict(
        self, img_fp: str
    ) -> sorter.classification_service.classification_result.ClassificationResult:
        if not isinstance(img_fp, str):
            raise Exception("Input must be string image file path")

        # load
        ocv_img = cv2.imread(img_fp)
        if ocv_img is None:
            raise InvalidImageError("Invalid image file")
        # ocv_img = sorter.white_balance.white_balance(ocv_img, random_whitebalance=False)
        ocv_img = cv2.cvtColor(ocv_img, cv2.COLOR_BGR2RGB)

        # crop and scale
        img_crop_low = sorter.classification_service.crop_image.crop_image(
            ocv_img, low=True
        )
        img_crop_high = sorter.classification_service.crop_image.crop_image(
            ocv_img, low=False
        )

        pred_low_list = self.predict_crop(img_crop_low, img_crop_high)
        pred_uniqueness = (
            pred_low_list[0]["probability"] / pred_low_list[1]["probability"]
        )

        return sorter.classification_service.classification_result.ClassificationResult(
            predicted_class=pred_low_list[0]["class"],
            predicted_class_high=pred_low_list[0]["class"],
            probability=pred_low_list[0]["probability"],
            uniqueness=pred_uniqueness,
            prediction_list=pred_low_list,
            label_data=None,
            low_list=pred_low_list,
            high_list=pred_low_list,
        )

    def predict_crop(self, img_crop_low, img_crop_high):
        import tensorflow as tf

        # convert to tensor
        image_array_low = tf.convert_to_tensor(img_crop_low, dtype=tf.float32)
        image_array_high = tf.convert_to_tensor(img_crop_high, dtype=tf.float32)

        # batch
        batch_low = tf.expand_dims(image_array_low, 0)
        batch_high = tf.expand_dims(image_array_high, 0)

        # predict
        probability = self.probability_model.predict((batch_low, batch_high), verbose=0)

        # class, prob, uniqueness
        # predicted_class = np.argmax(probability,1)
        probability_list = probability.tolist()[0]
        class_list = self.class_list
        pred_list = list(
            map(
                lambda t: {"class": t[0], "probability": t[1]},
                zip(class_list, probability_list),
            )
        )
        pred_list.sort(key=lambda a: a["probability"], reverse=True)

        return pred_list

    def get_class_count(self):
        return len(self.class_list)

    def class_name_from_index(self, index):
        return self.class_list[index]

    def class_index_from_name(self, name):
        if name not in self.class_list:
            return None

        return self.class_list.index(name)

    def get_class_list(self):
        return self.class_list
