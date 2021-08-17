import sys
import os

from utility.message import message_manager
from utility.logger import log
from utility.define import MessageType

from .camera import CameraSystem


def restart():
    os.system(f'start cmd /c {sys.executable} {" ".join(sys.argv)} 5')
    os._exit(0)


def start_slave():
    """Slave 總啟動程序"""
    log.info('Start slave')

    # 等待 Master 連接
    log.info('Wait for master connecting...')
    camera_system = None

    try:
        if not message_manager.is_connected():
            message = message_manager.receive_message()
            while message.type is not MessageType.MASTER_UP:
                continue

        # 相機系統初始化
        camera_system = CameraSystem()
        camera_system.start()

        is_master_down = False

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

    # if is_master_down:
    #     restart()
