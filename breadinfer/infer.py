import json
import os
from typing import Dict, Tuple

import cv2
import numpy as np
import supervision as sv
from inference_sdk import InferenceConfiguration, InferenceHTTPClient
from loguru import logger

mask_annotator = sv.MaskAnnotator()
label_annotator = sv.LabelAnnotator()
CLIENT = InferenceHTTPClient(
    api_url="https://outline.roboflow.com",
    api_key=os.environ.get("ROBOFLOW_API_KEY"),
)


def segmentation_from_imgpath(
    input_img_path: str = None, output_img_path: str = None
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
        raise ValueError("invalid image")
    if output_img_path is None:
        outputfolder = os.path.join(os.getcwd(), "output", "segmented")
        os.makedirs(outputfolder, exist_ok=True)
        output_img_path = os.path.join(outputfolder, os.path.basename(input_img_path))
    logger.info(f"Requesting Inference for Segmentation on: {input_img_path}")
    result = CLIENT.infer(input_img_path, model_id="bread-segmentation-hfhm8/4")

    image = cv2.imread(input_img_path)

    annotated_image = annotate_mask(image=image, result=result)
    # annotated_image = annotate_labels(image=annotated_image, result=result)

    cv2.imwrite(output_img_path, annotated_image)
    logger.info(f"Written image for Segmentation: {output_img_path}")
    return output_img_path, result


def annotate_labels(image: np.ndarray, result: dict) -> np.ndarray:
    """Input is Result from the inference
    Image is already read with imread

    Args:
        image (nparray): Image
        result (dict): Result from the API call for the model
    """
    try:
        labels = [item["class"] for item in result["predictions"]]
        detections = sv.Detections.from_inference(result)
        annotated = label_annotator.annotate(
            scene=image, detections=detections, labels=labels
        )
        return annotated
    except Exception as e:
        logger.warning(f"Error annotating labels: {e}")
        return image


def annotate_mask(image: np.ndarray, result: dict) -> np.ndarray:
    """Input is Result from the inference
    Image is already read with imread

    Args:
        image (_type_): _description_
        result (_type_): _description_
    """
    try:
        detections = sv.Detections.from_inference(result)
        reshaped_image = reshape_image_for_masking(image=image, mask=detections.mask)
        annotated = mask_annotator.annotate(scene=reshaped_image, detections=detections)
        return annotated
    except Exception as e:
        logger.error(f"Error annotating mask: {e}")
        raise


def reshape_image_for_masking(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
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
                reshaped_image, ((0, x_mask - x_img), (0, 0), (0, 0)), mode="constant"
            )
        if y_img > y_mask:
            # Slice the Y dimension
            reshaped_image[:, : mask.shape[2], :]
        elif y_img < y_mask:
            # Pad the Y dimension
            reshaped_image = np.pad(
                reshaped_image, ((0, 0), (0, y_mask - y_img), (0, 0)), mode="constant"
            )
        return reshaped_image


def labels_from_imgpath(input_img: str = None) -> Dict[str, float]:
    """Generate labels for the image

    Args:
        input_img (str, optional): Input image path. Defaults to None.

    Raises:
        ValueError: Raises error if input is null

    Returns:
        predictions:dict: predictions as key (name) and confidence (value)
    """
    # https://universe.roboflow.com/class-tu4kk/bread-seg/model/7
    if input_img is None:
        raise ValueError("invalid image")
    logger.info(f"Requesting label predictions for: {input_img}")

    result = CLIENT.infer(input_img, model_id="bread-seg/7")
    predictions = {
        prediction["class"]: prediction["confidence"]
        for prediction in result["predictions"]
    }
    logger.info(f"Label Predictions: {predictions}")
    return predictions


def map_confidence_to_sentiment(confidence: float, label: str) -> str:
    """Translate a confidence percentage to a text to indicate how accurate the elmeent is

    Args:
        confidence (float): Confidence value
        label (str): Label for the confidence

    Returns:
        str: Value for the confidence specified
    """
    if confidence < 0.5:
        return None
    elif confidence < 0.6:
        return "Weakly Negative"
    elif confidence < 0.7:
        return "Negative"
    elif confidence < 0.8:
        return "Somewhat Negative"
    elif confidence < 0.9:
        return "Neutral"
    elif confidence < 1.0:
        return "Somewhat Positive"
    else:
        return "Positive"


def get_message_content_from_labels(labels: list[str] = None) -> str:
    """Generate a message based on the input labels

    Args:
        labels (list[str], optional): Input labels. Defaults to None.

    Returns:
        str: Generated message to be used when sending
    """
    labeltext = ", ".join(labels.keys())
    return f"This is certainly bread! It seems to be {labeltext}"


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    input_img = "testdata/isometric/IMG_20240316_100329_589.jpg"
    output_img = "testdata/results/roboresult.png"
    labels = labels_from_imgpath(input_img=input_img)
    if "bread" in labels.keys():
        _, result = segmentation_from_imgpath(
            input_img=input_img, output_img=output_img
        )
