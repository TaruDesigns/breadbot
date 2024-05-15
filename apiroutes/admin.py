import os
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse, RedirectResponse

from breadinfer import inference
from discordroutes.botevents import bot

router = APIRouter()


@router.get("/status")
async def pingpong():  # Status check
    return {"status": "ok"}


@router.post("/senddm")
async def send_dm(msg: str, user_id: str = 206734328879775746):
    """Basic endpoint to test if the bot can send DMs

    Args:
        msg (str): _description_
        user_id (str, optional): _description_. Defaults to 206734328879775746.

    Returns:
        JSON: _description_
    """
    user = await send_message(msg, user_id)
    username = user["user"].global_name
    return {"message": f"'{msg}' sent to {username}"}


@router.post("/setinferconfidences")
async def set_infer_confidence(
    MIN_BREAD_LABEL_CONFIDENCE: Optional[float] = None,
    MIN_BREAD_SEG_CONFIDENCE: Optional[float] = None,
    FILTER_BREAD_LABEL_CONFIDENCE: Optional[float] = None,
    FILTER_BREAD_SEG_CONFIDENCE: Optional[float] = None,
    BREAD_DETECTION_CONFIDENCE: Optional[float] = None,
    OVERRIDE_DETECTION_CONFIDENCE: Optional[float] = None,
):
    """Endpoint to set bread inference confidences.Note that this will NOT reinstantiate the inference handler

    Args:
        MIN_BREAD_LABEL_CONFIDENCE (float, optional): Float, 0 to 1
        MIN_BREAD_SEG_CONFIDENCE (float, optional): Float, 0 to 1
        FILTER_BREAD_LABEL_CONFIDENCE (float, optional): Float, 0 to 1
        FILTER_BREAD_SEG_CONFIDENCE (float, optional): Float, 0 to 1
        BREAD_DETECTION_CONFIDENCE (float, optional): Float, 0 to 1
        OVERRIDE_DETECTION_CONFIDENCE (float, optional): Float, 0 to 1

    Returns:
        json: status ok
    """

    if MIN_BREAD_LABEL_CONFIDENCE is not None:
        os.environ["MIN_BREAD_LABEL_CONFIDENCE"] = str(MIN_BREAD_LABEL_CONFIDENCE)
    if MIN_BREAD_SEG_CONFIDENCE is not None:
        os.environ["MIN_BREAD_SEG_CONFIDENCE"] = str(MIN_BREAD_SEG_CONFIDENCE)
    if FILTER_BREAD_LABEL_CONFIDENCE is not None:
        os.environ["FILTER_BREAD_LABEL_CONFIDENCE"] = str(FILTER_BREAD_LABEL_CONFIDENCE)
    if FILTER_BREAD_SEG_CONFIDENCE is not None:
        os.environ["FILTER_BREAD_SEG_CONFIDENCE"] = str(FILTER_BREAD_SEG_CONFIDENCE)
    if BREAD_DETECTION_CONFIDENCE is not None:
        os.environ["BREAD_DETECTION_CONFIDENCE"] = str(BREAD_DETECTION_CONFIDENCE)
    if OVERRIDE_DETECTION_CONFIDENCE is not None:
        os.environ["OVERRIDE_DETECTION_CONFIDENCE"] = str(OVERRIDE_DETECTION_CONFIDENCE)

    return {"status": "ok"}


@router.post("/setroboflowargs")
async def set_roboflow_args(
    roboflow_endpoint: Optional[str] = "https://outline.roboflow.com",
    roboflow_apikey: Optional[str] = None,
):
    """Basic endpoint to set env vars for roboflow calls. Note that this will NOT reinstantiate the inference handler

    Args:
        roboflow_endpoint (_type_, optional): _description_. Defaults to "https://outline.roboflow.com".
        roboflow_apikey (Optional[str], optional): _description_. Defaults to None.

    Returns:
        _type_: _description_
    """
    os.environ["ROBOFLOW_API_KEY"] = str(roboflow_apikey)
    os.environ["ROFOBLOW_ENDPOINT"] = str(roboflow_endpoint)
    return {"status": "ok"}


@router.post("/reinitinference")
async def reinit_inference(
    local: bool = True,
    http_det_model: Optional[str] = "bread-seg/7",
    local_det_model: Optional[str] = "breadv7m-det.pt",
    http_seg_model: Optional[str] = "bread-segmentation-hfhm8/4",
    local_seg_model: Optional[str] = "breadsegv4m-seg.pt",
):
    # Reinit the inference model with new parameters
    inference.inferhandler = inference.InferenceHandler(
        local=local,
        http_det_model=http_det_model,
        http_seg_model=http_seg_model,
        local_det_model=local_det_model,
        local_seg_model=local_seg_model,
    )
    return {"status": "ok"}


@router.get("/checkcuda")
async def check_cuda():
    # Reinit the inference model with new parameters
    import torch

    try:
        results = {
            "cuda_available": torch.cuda.is_available(),
            "cuda_device": torch.cuda.current_device(),
            "cuda_device_count": torch.cuda.device_count(),
        }
    except:
        results = {"cuda": "no"}
    return results


async def send_message(message, user_id: str = 206734328879775746) -> str:
    # This is just a test function

    user = await bot.fetch_user(user_id)
    await user.send(message)
    return {
        "user": user,
        "message": message,
    }
