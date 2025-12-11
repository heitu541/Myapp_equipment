# src/utils.py - 修改后
from datetime import datetime
import hashlib
import streamlit as st
import logging

logger = logging.getLogger(__name__)

class Utils:
    """统一的工具函数类"""
    
    @staticmethod
    def get_preset_equipment():
        """获取预设实验设备列表 - 从数据库获取"""
        try:
            # 尝试从数据库获取
            if hasattr(st, 'session_state') and 'db_manager' in st.session_state:
                db_manager = st.session_state.db_manager
                if db_manager and hasattr(db_manager, 'get_all_equipment'):
                    devices = db_manager.get_all_equipment()
                    if devices:
                        return [device['name'] for device in devices]
            
            # 从 secrets.toml 中获取预设设备（作为回退）
            if hasattr(st, 'secrets') and 'equipment_presets' in st.secrets:
                devices = st.secrets['equipment_presets'].get('devices', [])
                if devices:
                    return devices
        
        except Exception as e:
            logger.error(f"获取预设设备失败: {e}")
        
        # 默认设备列表
        return [
            "疲劳性能试验机",
            "透射电子显微镜",
        ]
    
    @staticmethod
    def save_preset_equipment(devices):
        """保存预设设备列表到数据库"""
        try:
            if hasattr(st, 'session_state') and 'db_manager' in st.session_state:
                db_manager = st.session_state.db_manager
                if db_manager and hasattr(db_manager, 'sync_equipment'):
                    return db_manager.sync_equipment(devices)
            
            # 如果没有数据库管理器，回退到 secrets.toml
            return Utils._save_to_secrets(devices)
            
        except Exception as e:
            logger.error(f"保存预设设备失败: {e}")
            return False
    
    @staticmethod
    def _save_to_secrets(devices):
        """保存到 secrets.toml 文件（旧方法）"""
        try:
            import os
            import toml
            
            # 构造要写入的数据
            config_data = {
                'equipment_presets': {
                    'devices': devices
                }
            }
            
            # 写入到 secrets.toml 文件
            secrets_path = os.path.join('.streamlit', 'secrets.toml')
            with open(secrets_path, 'w', encoding='utf-8') as f:
                toml.dump(config_data, f)
            
            return True
        except Exception as e:
            print(f"保存到 secrets 失败: {e}")
            return False
    
    # 原有的其他方法保持不变...
    @staticmethod
    def safe_convert(value, target_type, default=None):
        """统一的类型安全转换"""
        if value is None or value == "":
            return default
        try:
            return target_type(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def validate_date(date_str):
        """验证日期格式"""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_time_format(t: str) -> bool:
        """验证时间格式"""
        try:
            datetime.strptime(t, "%H:%M")
            return True
        except ValueError:
            return False
    
    @staticmethod
    def hash_password(pwd: str) -> str:
        """计算密码的SHA256哈希值"""
        return hashlib.sha256(pwd.encode('utf-8')).hexdigest()
