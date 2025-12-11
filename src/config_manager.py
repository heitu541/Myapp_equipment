# src/config_manager.py
import logging
import os
import json

logger = logging.getLogger(__name__)

class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.config = {}
        self.load_config()
    
    def load_config(self):
        """加载配置"""
        try:
            # 尝试从配置文件加载
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                # 默认配置
                self.config = {
                    "default_admin_password": "9999",
                    "max_records_per_page": 200,
                    "timeout_seconds": 30
                }
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            self.config = {}
    
    def get_default_password_hash(self):
        """获取默认密码哈希值"""
        import hashlib
        default_pwd = self.config.get("default_admin_password", "9999")
        return hashlib.sha256(default_pwd.encode('utf-8')).hexdigest()
    
    def get(self, key, default=None):
        """获取配置值"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """设置配置值"""
        self.config[key] = value
        return self.save_config()
    
    def save_config(self):
        """保存配置到文件"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
