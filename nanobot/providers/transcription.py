"""使用Groq的语音转录提供者。

此模块实现了基于Groq Whisper API的语音转录功能。
Groq提供极快的转录速度，并有慷慨的免费额度。
"""

import os
from pathlib import Path
from typing import Any

import httpx
from loguru import logger


class GroqTranscriptionProvider:
    """
    使用Groq的Whisper API进行语音转录的提供者。
    
    Groq提供极快的转录速度，并有慷慨的免费额度。
    使用Whisper Large V3模型进行高精度转录。
    """
    
    def __init__(self, api_key: str | None = None):
        """
        初始化Groq转录提供者。
        
        Args:
            api_key: Groq API密钥，如果未提供则从环境变量获取
        """
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.api_url = "https://api.groq.com/openai/v1/audio/transcriptions"
    
    async def transcribe(self, file_path: str | Path) -> str:
        """
        使用Groq转录音频文件。
        
        将音频文件上传到Groq API进行转录，返回转录的文本。
        支持多种音频格式（mp3、wav、m4a等）。
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            转录的文本，如果出错则返回空字符串
        """
        if not self.api_key:
            logger.warning("Groq API key not configured for transcription")
            return ""
        
        path = Path(file_path)
        if not path.exists():
            logger.error(f"Audio file not found: {file_path}")
            return ""
        
        try:
            async with httpx.AsyncClient() as client:
                with open(path, "rb") as f:
                    files = {
                        "file": (path.name, f),
                        "model": (None, "whisper-large-v3"),
                    }
                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
                    }
                    
                    response = await client.post(
                        self.api_url,
                        headers=headers,
                        files=files,
                        timeout=60.0
                    )
                    
                    response.raise_for_status()
                    data = response.json()
                    return data.get("text", "")
                    
        except Exception as e:
            logger.error(f"Groq transcription error: {e}")
            return ""
