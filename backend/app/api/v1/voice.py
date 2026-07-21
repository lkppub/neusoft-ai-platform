from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io

from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/voice", tags=["语音"])


class TTSRequest(BaseModel):
    text: str
    voice: str | None = None
    rate: str | None = None


@router.post("/speech-to-text")
async def speech_to_text(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """语音转文字"""
    # Validate audio file
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="请上传音频文件")

    from app.services.voice.stt_service import get_stt_service
    stt = get_stt_service()

    audio_data = await file.read()

    try:
        text = await stt.transcribe(audio_data)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音识别失败: {e}")

    return {"text": text, "filename": file.filename}


@router.post("/text-to-speech")
async def text_to_speech(
    body: TTSRequest,
    current_user: User = Depends(get_current_user),
):
    """文字转语音"""
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="文本不能为空")

    from app.services.voice.tts_service import get_tts_service
    tts = get_tts_service()

    try:
        audio_data = await tts.synthesize(
            text=body.text,
            voice=body.voice,
            rate=body.rate or "+0%",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音合成失败: {e}")

    # Use the engine's declared audio format (MP3 for edge-tts, WAV for pyttsx3)
    media_type = getattr(tts, "audio_format", "audio/mpeg")

    return StreamingResponse(
        io.BytesIO(audio_data),
        media_type=media_type,
        headers={"Content-Disposition": "attachment; filename=speech.wav" if "wav" in media_type else "attachment; filename=speech.mp3"},
    )
