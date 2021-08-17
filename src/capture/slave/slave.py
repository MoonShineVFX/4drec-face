from utility.message import message_manager
from utility.logger import log
from utility.define import MessageType

from .camera import CameraSystem


def start_slave() -> int:
    """Slave 總啟動程序"""
    log.info('Start slave')

    # 等待 Master 連接
    log.info('Wait for master connecting...')
    camera_system = None
    is_master_down = False

    try:
        if not message_manager.is_connected():
            message = message_manager.receive_message()
            while message.type is not MessageType.MASTER_UP:
                continue

        # 相機系統初始化
        log.debug('Camera System initialize')
        camera_system = CameraSystem()
        camera_system.start()

        log.debug('MainProcess standby')
        while True:
            message = message_manager.receive_message()
            if message.type is MessageType.MASTER_DOWN:
                log.warning('Master Down !!')
                is_master_down = True
                break
    except KeyboardInterrupt:
        log.warning('Interrupted by keyboard!')

    log.info('Stop all connectors')

    try:
        if camera_system is not None:
            camera_system.stop()
        message_manager.stop()
    except Exception as error:
        log.warning(error)

    if is_master_down:
        return 4813

    return 0
