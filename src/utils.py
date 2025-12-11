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
            # 从数据库获取设备列表
            if hasattr(st, 'session_state') and 'db_manager' in st.session_state:
                db_manager = st.session_state.db_manager
                if db_manager and hasattr(db_manager, 'get_all_equipment'):
                    devices = db_manager.get_all_equipment()
                    if devices:
                        return [device['name'] for device in devices]
                    else:
                        logger.warning("数据库中没有找到设备记录")
                else:
                    logger.warning("数据库管理器未初始化或缺少get_all_equipment方法")
        
        except Exception as e:
            logger.error(f"获取预设设备失败: {e}")
        
        return []
    
    @staticmethod
    def save_preset_equipment(devices):
        """保存预设设备列表到数据库"""
        try:
            if hasattr(st, 'session_state') and 'db_manager' in st.session_state:
                db_manager = st.session_state.db_manager
                if db_manager and hasattr(db_manager, 'sync_equipment'):
                    success = db_manager.sync_equipment(devices)
                    if success:
                        logger.info(f"已同步 {len(devices)} 个设备到数据库")
                    else:
                        logger.error("同步设备到数据库失败")
                    return success
                else:
                    logger.error("数据库管理器未初始化或缺少sync_equipment方法")
                    return False
            
            logger.error("数据库管理器不可用")
            return False
            
        except Exception as e:
            logger.error(f"保存预设设备失败: {e}")
            return False
    
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