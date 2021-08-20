from loguru import logger
import sys


def get_prefix_log(prefix):
    """取得綁訂前贅字詞的 logger"""
    prefix_str = f'<{prefix}> '
    return logger.bind(prefix=prefix_str)


# log 格式
log_format = (
    '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> '
    '|<level>{level}</level>| '
    '<cyan>{name}:{function}:{line}</cyan> - '
    '<level>{extra[prefix]}{message}</level> '
    '({process.name})'
)
log_format_slave = (
    '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> '
    '|<level>{level}</level>| '
    '<cyan>[{extra[slave]}]</cyan> - '
    '<level>{message}</level>'
)


# log 總設定
logger.configure(
    handlers=[
        {'sink': sys.stderr, 'format': log_format, 'colorize': True, 'enqueue': True}
    ],
    extra={'prefix': ''}
)
