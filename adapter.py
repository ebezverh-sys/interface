import logging
from enum import Enum
from typing import Any
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# channel_id = "557cfd75-6f18-4e48-9af8-de9a2c40cbe6"
# platform_channel_url = f"https://http-adapter-demo03.mws.ai.local/api/{channel_id}"

REQUEST_TIMEOUT = 120


class MessageTypeEnum(str, Enum):
    TEXT = "text"

def get_session(user_id: str, platform_channel_url: str = None):
    if platform_channel_url is None:
        platform_channel_url = "https://http-adapter-demo03.mws.ai.local/api/557cfd75-6f18-4e48-9af8-de9a2c40cbe6"
    
    logger.debug(f"POST request to {platform_channel_url}")

    try:
        response = requests.post(
            verify=False,
            url=platform_channel_url,
            json={
                "payload": {"message": {"text": "start"}},
                "surfaceMetadata": {},
                "type": "text",
                "userId": user_id
            },
            timeout=REQUEST_TIMEOUT,
        )
        
        logger.info(f"Response status: {response.status_code}, time: {response.elapsed.total_seconds():.2f}s")
        response = response.json()
        session_id = None
        if isinstance(response, list):
            for response_item in response:
                if "sessionId" in response_item:
                    session_id = response_item["sessionId"]
                    break
        return session_id
    except requests.exceptions.Timeout:
        logger.error(f"Request timeout after {REQUEST_TIMEOUT}s")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise


def send_text(text: str, user_id: str, session_id: str = None, platform_channel_url: str = None):
    if platform_channel_url is None:
        platform_channel_url = "https://http-adapter-demo03.mws.ai.local/api/557cfd75-6f18-4e48-9af8-de9a2c40cbe6"
    
    logger.info(f"Sending text to engine, user_id={user_id}, platform_channel_url={platform_channel_url}, text_length={len(text)}")
    return send_to_engine(user_id, session_id, text=f"{text}", meta={"file": "None"}, platform_channel_url=platform_channel_url)


def send_to_engine(user_id: str, session_id: str = None, text: str = None, meta: dict[str, Any] = None, platform_channel_url: str = None):
    if platform_channel_url is None:
        platform_channel_url = "https://http-adapter-demo03.mws.ai.local/api/557cfd75-6f18-4e48-9af8-de9a2c40cbe6"
    
    # Убеждаемся, что meta - это словарь
    if meta is None:
        meta = {}
    
    logger.debug(f"POST request to {platform_channel_url}")

    try:
        request_json = {
            "payload": {"message": {"text": text}},
            "surfaceMetadata": meta,
            "type": "text",
            "userId": user_id
        }
        
        if session_id is not None:
            request_json["sessionId"] = session_id
            
        response = requests.post(
            verify=False,
            url=platform_channel_url,
            json=request_json,
            timeout=REQUEST_TIMEOUT,
        )
        logger.info(f"Response status: {response.status_code}, time: {response.elapsed.total_seconds():.2f}s")
        return response.json()
    except requests.exceptions.Timeout:
        logger.error(f"Request timeout after {REQUEST_TIMEOUT}s")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise
