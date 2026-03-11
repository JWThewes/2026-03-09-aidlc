"""Configuration for the code review agent."""
import os
from typing import Optional


class Config:
    """Configuration settings for the code review agent."""

    def __init__(self):
        self.aws_region: str = os.getenv("AWS_REGION", "us-east-1")
        self.bedrock_model_id: str = os.getenv(
            "BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0"
        )
        self.github_token: Optional[str] = os.getenv("GITHUB_TOKEN")
        self.s3_bucket: Optional[str] = os.getenv("S3_BUCKET")
        self.max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
        self.supported_languages: list = [
            "python",
            "javascript",
            "typescript",
            "java",
            "go",
            "rust",
            "c",
            "cpp",
        ]
        self.temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "10000"))


config = Config()
