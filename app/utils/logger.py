import logging
import os
from logging.handlers import RotatingFileHandler
from config import config

def setup_logger():
    # 创建日志目录
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # 创建日志记录器
    logger = logging.getLogger('expense_app')
    logger.setLevel(getattr(logging, config['default'].LOG_LEVEL))
    
    # 创建文件处理器
    file_handler = RotatingFileHandler(
        config['default'].LOG_FILE,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(getattr(logging, config['default'].LOG_LEVEL))
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, config['default'].LOG_LEVEL))
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到记录器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 创建全局日志记录器
logger = setup_logger() 