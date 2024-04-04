import json
import os

import cv2
import supervision as sv
from inference_sdk import InferenceConfiguration, InferenceHTTPClient
from loguru import logger

mask_annotator = sv.MaskAnnotator()
label_annotator = sv.LabelAnnotator()
CLIENT = InferenceHTTPClient(
    api_url="https://outline.roboflow.com",
    api_key=os.environ.get("ROBOFLOW_API_KEY"),
)


def segmentation_from_imgpath(input_img: str = None, output_img: str = None):
    # https://universe.roboflow.com/school-dkgod/bread-segmentation-hfhm8/model/4
    if input_img is None:
        raise ValueError("invalid image")
    if output_img is None:
        outputfolder = os.path.join(os.getcwd(), "output", "segmented")
        os.makedirs(outputfolder, exist_ok=True)
        output_img = os.path.join(outputfolder, os.path.basename(input_img))
    logger.info(f"Requesting Inference for Segmentation on: {input_img}")
    result = CLIENT.infer(input_img, model_id="bread-segmentation-hfhm8/4")

    image = cv2.imread(input_img)

    annotated_image = annotate_mask(image=image, result=result)
    annotated_image = annotate_labels(image=annotated_image, result=result)

    cv2.imwrite(output_img, annotated_image)
    logger.info(f"Written image for Segmentation: {output_img}")
    return output_img, result


def annotate_labels(image, result):
    """Input is Result from the inference
    Image is already read with imread

    Args:
        image (_type_): _description_
        result (_type_): _description_
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


def annotate_mask(image, result):
    """Input is Result from the inference
    Image is already read with imread

    Args:
        image (_type_): _description_
        result (_type_): _description_
    """
    try:
        detections = sv.Detections.from_inference(result)
        annotated = mask_annotator.annotate(scene=image, detections=detections)
        return annotated
    except Exception as e:
        logger.error(f"Error annotating mask: {e}")
        raise


def labels_from_imgpath(input_img: str = None):
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


def map_confidence_to_sentiment(confidence: float, label: str):
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


def get_message_content_from_labels(labels: list[str] = None):
    # TODO
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
