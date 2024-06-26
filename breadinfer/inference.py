import asyncio
import json
import os
import shutil
from typing import Dict, Tuple

import cv2
import numpy as np
from loguru import logger


class InferenceHandler:
    """Main Inference class, works for both local and http requests (roboflow) based on the input parameter. Default is local model"""

    def __init__(
        self,
        local: bool = True,
        http_det_model: str = "bread-seg/7",
        local_det_model: str = "breadv7m-det.pt",
        http_seg_model: str = "bread-segmentation-hfhm8/4",
        local_seg_model: str = "breadsegv4m-seg.pt",
    ):
        self._local = local
        if local:
            logger.info("Loading inference models: Local")
            from ultralytics import YOLO

            self.local_det_model = YOLO(
                os.path.join("yolov8", "trainedmodels", local_det_model)
            )
            self.local_seg_model = YOLO(
                os.path.join("yolov8", "trainedmodels", local_seg_model)
            )
        else:
            import supervision as sv
            from inference_sdk import InferenceConfiguration, InferenceHTTPClient

            logger.info("Loading inference models: HTTP")
            self.http_mask_annotator = sv.MaskAnnotator()
            self.http_label_annotator = sv.LabelAnnotator()
            self.http_client = InferenceHTTPClient(
                api_url=os.environ.get("ROFOBLOW_ENDPOINT"),
                api_key=os.environ.get("ROBOFLOW_API_KEY"),
            )
            self.http_det_model = http_det_model
            self.http_seg_model = http_seg_model
        ...

    async def async_labels_from_imgpath(
        self, input_img_path: str = None, confidence: float = None
    ):
        """Async helper to run inference on detection(labels)

        Args:
            filename (_type_): _description_

        Returns:
            _type_: _description_
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.labels_from_imgpath, input_img_path, confidence
        )

    async def async_segmentation_from_imgpath(
        self,
        input_img_path: str = None,
        output_img_path: str = None,
        confidence: float = None,
    ) -> Tuple[str, Dict]:
        """Async helper to run inference on segmentation

        Args:
            input_img_path (str): _description_
            output_img_path (str): _description_

        Returns:
            Tuple[str, Dict]: _description_
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.segmentation_from_imgpath,
            input_img_path,
            output_img_path,
            confidence,
        )

    def segmentation_from_imgpath(
        self,
        input_img_path: str = None,
        output_img_path: str = None,
        confidence: float = None,
    ) -> Tuple[str, dict]:
        """Creates segmentation image
        Uses model from https://universe.roboflow.com/school-dkgod/bread-segmentation-hfhm8/model/4
        Creates a new image that has the segmented bread drawn over it. Returns image path and the results (json object)
        Args:
            input_img (str, optional): Input image path. Defaults to None.
            output_img (str, optional): Output image path to be written to. Defaults to None: If None, it will be saved on default location.

        Raises:
            ValueError: Raise error if input image is not provided

        Returns:
            output_img_path: path of the saved file (will match output_img_path if it's not null)
            result: json object with the results from the API
        """

        if input_img_path is None:
            raise ValueError("Invalid image")
        if confidence is None:
            confidence = float(os.environ.get("MIN_BREAD_SEG_CONFIDENCE"))
        if output_img_path is None:
            # Default to standard output folder
            outputfolder = os.path.join(os.getcwd(), "output", "segmented")
            os.makedirs(outputfolder, exist_ok=True)
            output_img_path = os.path.join(
                outputfolder, os.path.basename(input_img_path)
            )
        else:
            # Create output folder as requested
            outputfolder = os.path.dirname(output_img_path)
            os.makedirs(outputfolder, exist_ok=True)
        if self._local:
            # Get inference and file from computing with local YOLOv8 model
            logger.info(f"Computing local inference for segmentation: {input_img_path}")
            results = self.local_seg_model.predict(
                input_img_path,
                save=True,
                device="cpu",
                conf=confidence,
                project="output",
                name="segmented",
                exist_ok=True,
                show_labels=False,
                show_conf=False,
                show_boxes=False,
            )
            if results and results[0].masks is not None:
                # It's saved when running predict but we can't set the path directly so we retrieve it here and moved to destination path
                temp_filepath = os.path.join(
                    results[0].save_dir, os.path.basename(results[0].path)
                )
                logger.debug(f"Moving from {temp_filepath} to {output_img_path}")
                shutil.move(temp_filepath, output_img_path)
                logger.debug(f"File moved from {temp_filepath} to {output_img_path}")
                return output_img_path, results
            else:
                return None, None
        else:
            logger.info(f"Requesting Inference for Segmentation on: {input_img_path}")
            result = self.http_client.infer(
                input_img_path, model_id=self.http_seg_model
            )
            image = cv2.imread(input_img_path)
            annotated_image = self.annotate_mask(image=image, result=result)
            cv2.imwrite(output_img_path, annotated_image)
            logger.info(f"Written image for Segmentation: {output_img_path}")
            return output_img_path, result

    def annotate_labels(self, image: np.ndarray, result: dict) -> np.ndarray:
        """Input is Result from the inference
        Image is already read with imread

        Args:
            image (nparray): Image
            result (dict): Result from the API call for the model
        """
        if self._local:
            ...  # TODO add local labels
            raise NotImplementedError(
                "Annotating labels with local model returns a written image path"
            )
        else:
            import supervision as sv

            try:
                labels = [item["class"] for item in result["predictions"]]
                detections = sv.Detections.from_inference(result)
                annotated = self.http_label_annotator.annotate(
                    scene=image, detections=detections, labels=labels
                )
                return annotated
            except Exception as e:
                logger.warning(f"Error annotating labels: {e}")
                return image

    def annotate_mask(self, image: np.ndarray, result: dict) -> np.ndarray:
        """Input is Result from the inference
        Image is already read with imread

        Args:
            image (_type_): _description_
            result (_type_): _description_
        """
        if self._local:
            raise NotImplementedError(
                "Predict with local model will already write labels, use that "
            )
        else:
            import supervision as sv

            try:
                detections = sv.Detections.from_inference(result)
                reshaped_image = self.reshape_image_for_masking(
                    image=image, mask=detections.mask
                )
                annotated = self.http_mask_annotator.annotate(
                    scene=reshaped_image, detections=detections
                )
                return annotated
            except Exception as e:
                logger.error(f"Error annotating mask: {e}")
                raise

    def reshape_image_for_masking(
        self, image: np.ndarray, mask: np.ndarray
    ) -> np.ndarray:
        """Helper function to reshape image for masking
        Dimensions must match for the mask annotator to work

        Args:
            image (_type_): Original image
            mask (_type_): Mask (detections.mask)

        Returns:
            image: Reshaped image
        """
        # Detections mask shape is (1, x, y)
        # Image shape (BGR) is (x, y, 3)
        x_img, y_img = image.shape[0], image.shape[1]
        x_mask, y_mask = mask.shape[1], mask.shape[2]
        reshaped_image = image  # Init reshaped image as same dimension
        if x_img >= x_mask and y_img >= y_mask:
            # Original image is bigger or already the same so we just slice it
            return reshaped_image[: mask.shape[1], : mask.shape[2], :]
        else:
            if x_img > x_mask:
                # Slice the X dimension
                reshaped_image = reshaped_image[: mask.shape[1], :, :]
            elif x_img < x_mask:
                # Pad the X dimensions
                reshaped_image = np.pad(
                    reshaped_image,
                    ((0, x_mask - x_img), (0, 0), (0, 0)),
                    mode="constant",
                )
            if y_img > y_mask:
                # Slice the Y dimension
                reshaped_image[:, : mask.shape[2], :]
            elif y_img < y_mask:
                # Pad the Y dimension
                reshaped_image = np.pad(
                    reshaped_image,
                    ((0, 0), (0, y_mask - y_img), (0, 0)),
                    mode="constant",
                )
            return reshaped_image

    def labels_from_imgpath(
        self, input_img_path: str = None, confidence: float = None
    ) -> Dict[str, float]:
        """Generate labels for the image

        Args:
            input_img (str, optional): Input image path. Defaults to None.

        Raises:
            ValueError: Raises error if input is null

        Returns:
            predictions:dict: predictions as key (name) and confidence (value)
        """
        # https://universe.roboflow.com/class-tu4kk/bread-seg/model/7
        if input_img_path is None:
            raise ValueError("invalid image")
        if confidence is None:
            confidence = float(os.environ.get("MIN_BREAD_LABEL_CONFIDENCE"))
        if self._local:
            # Compute inference with local model
            logger.info(f"Computing label predictions for: {input_img_path}")
            results = self.local_det_model.predict(
                input_img_path,
                save=False,
                device="cpu",
                conf=confidence,
            )
            if results:
                resulttojson = json.loads(
                    results[0].tojson()
                )  # We already check if there's any and we only expect one image when we call this
                predictions = {
                    prediction["name"]: prediction["confidence"]
                    for prediction in resulttojson
                }
            else:
                predictions = {}
            logger.info(f"Label Predictions: {predictions}")
            return predictions
        else:
            # Compute with Roboflow
            logger.info(f"Requesting label predictions for: {input_img_path}")
            result = self.http_client.infer(
                input_img_path, model_id=self.http_det_model
            )
            predictions = {
                prediction["class"]: prediction["confidence"]
                for prediction in result["predictions"]
            }
            logger.info(f"Label Predictions: {predictions}")
            return predictions

    def map_confidence_to_sentiment(self, confidence: float, label: str) -> str:
        """Translate a confidence percentage to a text to indicate how accurate the element is

        Args:
            confidence (float): Confidence value
            label (str): Label for the confidence

        Returns:
            str: Value for the confidence specified
        """
        label = label.replace("_", " ")
        if confidence < 0.5:
            return f"{label}, H E L P, "
        elif confidence < 0.6:
            return f", just a bit {label}"
        elif confidence < 0.7:
            return f"reasonably {label}"
        elif confidence < 0.8:
            return f"probably {label}"
        elif confidence < 0.9:
            return f"fairly confident that it's {label}"
        elif confidence < 1.0:
            return f"pretty sure it is {label}"
        else:
            return f"Confirmed that it's {label}"

    def get_message_content_from_labels(
        self, predictions: Dict[str, float] = None, min_confidence: float = None
    ) -> str:
        """Generate a message based on the input labels

        Args:
            labels (list[str], optional): Input labels. Defaults to None.

        Returns:
            str: Generated message to be used when sending
        """
        if min_confidence is None:
            min_confidence = os.environ.get("FILTER_BREAD_LABEL_CONFIDENCE")
        labeltext = "This is certainly bread! "
        for label, confidence in predictions.items():
            if confidence >= min_confidence:
                labeltext = (
                    labeltext
                    + self.map_confidence_to_sentiment(
                        confidence=confidence, label=label
                    )
                    + " "
                )
        logger.debug(labeltext)
        return labeltext

    def estimate_roundness_from_mask(self, results) -> float:
        """Estimates roundness from mask, based on how close it is to a perfect circunscribed circle

        Args:
            results (float): percentage (0 to 1) of roundness

        Raises:
            ValueError: _description_
            ValueError: _description_
            ValueError: _description_

        Returns:
            float: _description_
        """
        if results and results[0].masks is not None:
            orig_shape = results[0].masks.orig_shape
            mask = results[0].masks.xy
        else:
            raise ValueError("No masks to read")
        if orig_shape is None:
            raise ValueError("Orig Shape is mandatory")
        if mask is None:
            raise ValueError("Mask is mandatory")
        black_image = np.zeros(
            (orig_shape[0], orig_shape[1], 3), dtype=np.uint8
        )  # Empty image to draw lines and use to estimate contours
        cv2.polylines(black_image, np.int32([mask]), True, (255, 255, 255), 2)
        gray_image = cv2.cvtColor(
            black_image, cv2.COLOR_BGR2GRAY
        )  # Polylines turns the image to BGR so we need to turn it back to grayscale
        # Find contours in the mask
        contours, _ = cv2.findContours(
            gray_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        # Assuming there's only one closed contour
        if contours:
            contour = contours[0]
            # Calculate area of the contour
            area = cv2.contourArea(contour)
            # Calculate minimum enclosing circle and its area
            (x, y), radius = cv2.minEnclosingCircle(contour)
            circle_area = np.pi * radius**2
            # Calculate roundness (ratio of contour area to area of minimum enclosing circle)
            roundness = area / circle_area
            return roundness
        else:
            return None

    def get_message_from_roundness(self, roundness: float = None):
        if roundness is None:
            return "I don't think this bread is round at all..."
        messagecontent = f"This bread seems {round(roundness * 100, 2):.2f}% round. Anything over an 80% is pretty close to a sphere!"
        logger.debug(messagecontent)
        return messagecontent


# Default inference handler with local models ready to import
inferhandler = InferenceHandler(local=True)

if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    inferhandler = InferenceHandler(local=True)

    input_img = "downloads/IMG_3904.png"
    output_img = "output/segmented/roboresult.png"

    labels = inferhandler.labels_from_imgpath(input_img_path=input_img)
    if "bread" in labels.keys():
        _, result = inferhandler.segmentation_from_imgpath(
            input_img_path=input_img, output_img_path=output_img
        )
        print("A")
