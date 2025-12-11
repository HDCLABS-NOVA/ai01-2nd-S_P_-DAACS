import os
import logging
from typing import Optional

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("DAACS")

def setup_logger(name: str) -> logging.Logger:
    """모듈별 로거를 생성합니다."""
    return logging.getLogger(name)

def read_file(file_path: str) -> Optional[str]:
    """파일 내용을 읽어옵니다."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        return None

def write_file(file_path: str, content: str) -> bool:
    """파일에 내용을 씁니다."""
    try:
        dir_path = os.path.dirname(file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"File written: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        return False
