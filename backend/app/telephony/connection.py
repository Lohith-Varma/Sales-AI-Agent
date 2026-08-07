import json
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def parse_twilio_media_frame(message_text: str) -> Optional[bytes]:
    """
    Parses a Twilio WebSocket message.
    If the event is 'media', extracts and decodes the base64 audio payload.
    
    Twilio media streams payload format:
    {
      "event": "media",
      "streamSid": "MZ...",
      "media": {
        "track": "inbound",
        "chunk": "1",
        "timestamp": "870",
        "payload": "base64String..."
      }
    }
    """
    try:
        data = json.loads(message_text)
        event = data.get("event")
        
        if event == "connected":
            logger.info(f"Twilio Stream Connected: Protocol: {data.get('protocol')}, Version: {data.get('version')}")
            return None
        elif event == "start":
            logger.info(f"Twilio Stream Started. Metadata: {data.get('start')}")
            return None
        elif event == "media":
            payload = data["media"]["payload"]
            return base64.b64decode(payload)
        elif event == "stop":
            logger.info("Twilio Stream Stopped.")
            return None
    except Exception as e:
        logger.error(f"Error parsing Twilio media frame: {e}")
        return None
    return None
