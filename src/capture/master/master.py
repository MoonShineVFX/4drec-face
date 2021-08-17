import sys
import os


def start_master() -> int:
    """master 總啟動程序"""
    from utility.message import message_manager
    from utility.logger import log
    from utility.define import MessageType

    from .ui import ui  # 初始化 UI
    from .hardware_trigger import hardware_trigger
    from .camera import camera_manager
    from .resolve import resolve_manager

    log.info('Start Master')
    ui.show()

    try:
        while True:
            # Message 接收與觸發
            message = message_manager.receive_message()

            if (
                message.type is MessageType.LIVE_VIEW_IMAGE or
                message.type is MessageType.SHOT_IMAGE
            ):
                camera_manager.receive_image(message)

            elif message.type is MessageType.CAMERA_STATUS:
                camera_manager.update_status(message)

            elif message.type is MessageType.SLAVE_DOWN:
                camera_manager.stop_capture(message)

            elif message.type is MessageType.MASTER_DOWN:
                log.warning('Master closed')
                break

            elif message.type is MessageType.RECORD_REPORT:
                camera_manager.collect_report(message)

            elif message.type is MessageType.SUBMIT_REPORT:
                camera_manager.collect_report(message)

            elif message.type is MessageType.TRIGGER_REPORT:
                camera_manager.collect_report(message)
    except KeyboardInterrupt:
        log.warning('Interrupted by keyboard!')

    message_manager.send_message(MessageType.MASTER_DOWN)

    # 關閉通訊
    hardware_trigger.close()
    message_manager.stop()

    return 0
