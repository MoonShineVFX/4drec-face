import loguru
from loguru import logger
import sys

# log 格式
log_format = (
    '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> '
    '|<level>{level}</level>| '
    '<cyan>{name}:{function}:{line}</cyan> - '
    '<level>{extra[prefix]}{message}</level> '
    '({process.name})'
)


# log 總設定
logger.configure(
    handlers=[
        {'sink': sys.stderr, 'format': log_format, 'colorize': True, 'enqueue': True}
    ],
    extra={'prefix': ''}
)

log = logger.bind(prefix='<29445237(12)> ')


# test
log.info('test')


def new_sink(message):
    require_restart = message.record['level'].name == 'CRITICAL'
    print(f'send to master: {str(message)}, require_start={require_restart}')


log.add(sink=new_sink, format='{extra[prefix]}{message}', level='ERROR')

log.info('hi this info')
log.error('and sometihng error')
log.critical('wow holy shit!!')