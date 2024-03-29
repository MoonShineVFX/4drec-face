import yaml
import os
import platform
import sys
from pathlib import Path
import json

from common.camera_structure.camera_structure import CameraStructure


SETTINGS_YAML_PATH = Path(__file__) / '../../settings'


class SettingManager(CameraStructure):
    """設定管理

    將 settings 資料夾的所有 yaml 設定檔整合
    取得設定資訊的方式是以 property 的方式，取代字典拿法的不便

    """

    def __init__(self):
        super().__init__()
        self._settings = {}  # 設定資料

        # 蒐集所有 settings 資料夾的 yaml 檔案
        files = list(SETTINGS_YAML_PATH.glob('*.yaml'))
        for file in files:
            with open(str(file), 'r') as f:
                self._settings.update(yaml.load(f, Loader=yaml.FullLoader))

        # 如果是 slave 就建立錄製資料夾
        if not self.is_master():
            self._make_record_folder()
        # 如果是 master 以及有 conda 環境變數的狀況，assign 環境變數
        else:
            python_path = Path(sys.executable).parents[0]
            state_path = python_path / 'conda-meta/state'
            if state_path.is_file():
                with open(str(state_path), 'r') as f:
                    data = json.load(f)
                envs = data.get('env_vars', None)
                if envs is not None:
                    for key, value in envs.items():
                        os.environ[key] = value

    def __getattr__(self, attr):
        """取得設定檔資訊，是字典的話會以 SettingProperty 包裝回傳"""
        if attr not in self._settings:
            raise AttributeError(
                f'[{attr}] not found in settings'
            )

        value = self._settings[attr]

        # 判斷是否是字典
        if isinstance(value, dict):
            return SettingProperty(value)
        else:
            return value

    def _make_record_folder(self):
        """創建錄製用資料夾

        檢查電腦有沒有錄製用的資料夾，沒有的話就創建

        """
        for drive in self.record.drives:
            path = f'{drive}:/{self.record.folder_name}/'
            os.makedirs(path, exist_ok=True)

    @staticmethod
    def is_master():
        """確認是否是 master"""
        return os.environ['4DREC_TYPE'] == 'MASTER'

    def get_host_address(self):
        """取得 Master 連線地址"""
        return (
            self.host_address.ip,
            self.host_address.port
        )

    def get_record_folder_path(self, camera_index):
        """取得錄製路徑

        藉由順序，輪流分配所設定的硬碟數量產生的路徑

        """
        drives = self.record.drives
        idx = camera_index % len(drives)
        drive = drives[idx]
        folder = self.record.folder_name
        return f'{drive}:/{folder}/'

    def get_shot_file_path(self, shot_id, camera_id):
        folder = self.record.folder_name
        for drive in self.record.drives:
            file_path = f'{drive}:/{folder}/{shot_id}/{camera_id}'
            if os.path.isfile(file_path + '.4dr'):
                return file_path
        return None

    def get_slave_cameras_count(self):
        return self.slaves[platform.node()]

    def get_slave_index(self):
        return list(self.slaves.keys()).index(platform.node())

    @staticmethod
    def get_slave_name() -> str:
        return platform.node()

    def save_camera_parameters(self, parms):
        save_parms = {'camera_user_parameters': parms}
        with open(str(SETTINGS_YAML_PATH / 'user_parameters.yaml'), 'w') as f:
            yaml.dump(save_parms, f)
        self._settings.update(save_parms)

    def has_user_parameters(self):
        return 'camera_user_parameters' in self._settings

    def apply(self, data):
        self._settings.update(data)

    @staticmethod
    def is_testing():
        return os.environ.get('testing', None) is not None


class SettingProperty(dict):
    """屬性包裝

    繼承字典，並將字典包裝起來以 property 的方式回傳

    Args:
        value: 值

    """

    def __init__(self, value):
        super().__init__()
        self.update(value)

    def __getattr__(self, attr):
        if attr not in self:
            raise AttributeError(
                f'{attr} not found in {self}'
            )

        value = self[attr]
        if isinstance(value, dict):
            return SettingProperty(value)
        else:
            return value


setting = SettingManager()  # 單例模式
