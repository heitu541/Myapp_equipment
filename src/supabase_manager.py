# src/supabase_manager.py - 优化版本
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
import logging
import sys
import os

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

logger = logging.getLogger(__name__)

class SupabaseManager:
    """Supabase数据库管理器"""
    
    def __init__(self):
        try:
            from supabase_client import SupabaseClient
            from config_manager import ConfigManager
            
            self.client = SupabaseClient()
            self.config_manager = ConfigManager()
            self.init_tables()
            
        except ImportError as e:
            logger.error(f"导入依赖模块失败: {e}")
            self.client = None
            self.config_manager = None
    
    def init_tables(self):
        """初始化数据库表结构"""
        if self.client is None:
            logger.warning("Supabase客户端未初始化")
            return False
            
        try:
            # 检查表是否存在
            try:
                self.client.select('entries', limit=1)
                logger.info("数据库表检查完成")
                
                # 初始化设置
                self.init_default_settings()
                return True
                
            except Exception as e:
                logger.error(f"表检查失败: {e}")
                logger.info("请确保在Supabase中创建了entries和settings表")
                return False
                
        except Exception as e:
            logger.error(f"初始化表失败: {e}")
            return False
    
    def init_default_settings(self):
        """初始化默认设置"""
        if self.client is None or self.config_manager is None:
            return False
            
        try:
            # 检查是否已有设置
            existing_settings = self.client.select('settings')
            
            # 如果没有设置，创建默认设置
            if not existing_settings:
                default_password_hash = self.config_manager.get_default_password_hash()
                default_settings = [
                    {"key": "admin_password_hash", "value": default_password_hash},
                ]
                
                for setting in default_settings:
                    self.client.insert('settings', setting)
                
                logger.info("默认设置已初始化")
            
            return True
                
        except Exception as e:
            logger.error(f"初始化默认设置失败: {e}")
            return False
    
    def get_setting(self, key: str, default=None) -> Any:
        """获取设置值"""
        if self.client is None:
            # 如果客户端未初始化，返回配置管理器的默认值
            if key == "admin_password_hash" and self.config_manager:
                return self.config_manager.get_default_password_hash()
            return default
            
        try:
            result = self.client.select('settings', conditions={"key": key})
            
            if result:
                return result[0]['value']
            elif key == "admin_password_hash" and self.config_manager:
                # 数据库中没有，使用配置管理器的默认值
                return self.config_manager.get_default_password_hash()
            else:
                return default
                
        except Exception as e:
            logger.error(f"获取设置失败: {e}")
            return default
    
    def set_setting(self, key: str, value: str) -> bool:
        """设置值"""
        if self.client is None:
            return False
            
        try:
            existing = self.client.select('settings', conditions={"key": key})
            
            if existing:
                # 更新现有设置
                success = self.client.update('settings', {"value": value}, existing[0]['id'])
            else:
                # 插入新设置
                success = self.client.insert('settings', {"key": key, "value": value})
            
            return success is not None
                
        except Exception as e:
            logger.error(f"设置值失败: {e}")
            return False
    
    def _sanitize_record_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清理和验证记录数据"""
        from utils import Utils
        
        sanitized = {
            'test_date': data.get('test_date', ''),
            'test_time': data.get('test_time') or '',
            'name': data.get('name', '').strip(),
            'contact': data.get('contact', '').strip() or None,
            'advisor': data.get('advisor', '').strip() or None,
            'equipment': data.get('equipment', '').strip() or None,
            'machine_hours': Utils.safe_convert(data.get('machine_hours'), float, 0.0),
            'cost': Utils.safe_convert(data.get('cost'), int, 0),
            'remark': data.get('remark', '').strip() or None
        }
        
        return sanitized
    
    def save_record(self, data: Dict[str, Any], record_id: Optional[int] = None) -> bool:
        """保存记录（插入或更新）"""
        if self.client is None:
            logger.error("数据库客户端未初始化")
            return False
            
        try:
            # 验证必要字段
            if not data.get('test_date') or not data.get('name') or not data.get('equipment'):
                logger.error("缺少必要字段: test_date, name 或 equipment")
                return False
            
            # 清理数据
            sanitized = self._sanitize_record_data(data)
            from datetime import datetime
            now = datetime.now()
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")
            
            record_data = {
                **sanitized,
                'last_modified': now_str
            }
            
            if record_id:  # 更新记录
                # 保留原始登记时间
                existing = self.get_record_by_id(record_id)
                if existing:
                    record_data['register_datetime'] = existing.get('register_datetime', now)
                    record_data['created_at'] = existing.get('created_at', now.split('T')[0])
                
                result = self.client.update('entries', record_data, record_id)
                logger.info(f"更新记录 {record_id}: {record_data.get('name')}")
                return result is not None
                
            else:  # 插入新记录
                record_data['register_datetime'] = now_str
            record_data['created_at'] = now.strftime("%Y-%m-%d")
                
                result = self.client.insert('entries', record_data)
                logger.info(f"插入新记录: {record_data.get('name')}")
                return result is not None
                
        except Exception as e:
            logger.error(f"保存记录失败: {e}")
            return False
    
    def delete(self, table: str, record_id: int):
        """删除数据"""
        if not self.client:
            return False
        try:
            response = self.client.table(table).delete().eq('id', record_id).execute()
            # 检查是否成功删除
            if hasattr(response, 'data'):
                return True
            return False
        except Exception as e:
            logger.error(f"删除失败: {e}")
            return False
    
    # 在 supabase_manager.py 的 get_records() 方法中，修改日期过滤逻辑：
    def get_records(self, 
                    conditions: Optional[Dict[str, Any]] = None,
                    date_range: Optional[tuple] = None,
                    date_field: str = "test_date",  # 新增参数，指定日期字段
                    order_by: str = "test_date DESC, id DESC",
                    limit: int = 200) -> List[Dict[str, Any]]:
        """查询记录 - 修复数据库连接问题"""
        if self.client is None:
            logger.warning("数据库客户端未初始化")
            return []
        
        try:
            # 安全限制
            safe_limit = min(limit, 500) if limit else 200
            
            # 构建查询条件
            query_conditions = {}
            if conditions:
                for field, value in conditions.items():
                    if value is not None and value != '':
                        query_conditions[field] = value
            
            logger.info(f"查询条件: {query_conditions}, 日期范围: {date_range}, 日期字段: {date_field}, 排序: {order_by}")
            
            # 先尝试简单查询测试连接
            try:
                test_result = self.client.select('entries', limit=1)
                logger.info(f"数据库连接测试成功，表中有 {len(test_result) if test_result else 0} 条记录")
            except Exception as e:
                logger.error(f"数据库连接测试失败: {e}")
                return []
            
            # 执行查询
            records = self.client.select('entries', 
                                    conditions=query_conditions if query_conditions else None,
                                    order_by=order_by,
                                    limit=safe_limit)
            
            logger.info(f"查询到 {len(records)} 条记录")
            
            # 日期范围过滤（基于指定的日期字段）
            if date_range and len(date_range) == 2 and records:
                start_date, end_date = date_range
                filtered_records = []
                for record in records:
                    # 根据指定的日期字段获取日期
                    record_date_str = None
                    if date_field == "register_datetime":
                        # 从登记时间中提取日期部分
                        register_datetime = record.get('register_datetime', '')
                        if register_datetime:
                            # 处理ISO格式
                            if 'T' in register_datetime:
                                try:
                                    dt = datetime.fromisoformat(register_datetime.replace('Z', '+00:00'))
                                    record_date_str = dt.date().isoformat()
                                except:
                                    record_date_str = register_datetime.split('T')[0]
                            else:
                                record_date_str = register_datetime.split(' ')[0]  # 处理空格分隔格式
                    else:
                        # 默认使用test_date
                        record_date_str = record.get(date_field, '')
                    
                    if record_date_str and start_date <= record_date_str <= end_date:
                        filtered_records.append(record)
                records = filtered_records
                logger.info(f"基于 {date_field} 日期范围过滤后剩余 {len(records)} 条记录")
            
            return records
            
        except Exception as e:
            logger.error(f"查询记录失败: {e}")
            # 返回空列表而不是抛出异常
            return []
        
    def get_records_as_tuples(self, 
                            conditions: Optional[Dict[str, Any]] = None,
                            date_range: Optional[tuple] = None,
                            date_field: str = "test_date",  # 新增参数
                            order_by: str = "test_date DESC, id DESC",
                            limit: int = 200) -> List[tuple]:
        """获取记录并转换为元组格式（兼容旧接口）"""
        try:
            # 调用 get_records() 并传递所有参数
            records = self.get_records(
                conditions=conditions,
                date_range=date_range,
                date_field=date_field,  # 传递 date_field 参数
                order_by=order_by,
                limit=limit
            )
            
            if not records:
                logger.info("没有查询到记录")
                return []
            
            result = []
            for record in records:
                try:
                    # 处理登记时间格式
                    register_datetime = record.get('register_datetime', '')
                    if register_datetime and isinstance(register_datetime, str):
                        # 如果是ISO格式，尝试格式化
                        if 'T' in register_datetime:
                            try:
                                dt = datetime.fromisoformat(register_datetime.replace('Z', '+00:00'))
                                register_datetime = dt.strftime("%Y-%m-%d %H:%M:%S")
                            except:
                                pass
                    
                    record_tuple = (
                        record.get('id'),
                        register_datetime,
                        record.get('test_date', ''),
                        record.get('test_time', ''),
                        record.get('name', ''),
                        record.get('contact', ''),
                        record.get('advisor', ''),
                        record.get('equipment', ''),
                        record.get('machine_hours', 0.0),
                        record.get('cost', 0),
                        record.get('remark', ''),
                        record.get('created_at', ''),
                        record.get('last_modified', '')
                    )
                    result.append(record_tuple)
                except Exception as e:
                    logger.error(f"转换记录失败: {e}, 记录: {record}")
                    continue
            
            logger.info(f"成功转换 {len(result)} 条记录为元组格式")
            return result
            
        except Exception as e:
            logger.error(f"获取记录元组失败: {e}")
            return []
    
    def search_records(self, 
                      keywords: Optional[str] = None,
                      advisor: Optional[str] = None,
                      equipment: Optional[str] = None,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None,
                      limit: int = 100) -> List[Dict[str, Any]]:
        """高级搜索记录"""
        if self.client is None:
            return []
            
        try:
            conditions = {}
            
            if advisor:
                conditions['advisor'] = advisor
            if equipment:
                conditions['equipment'] = equipment
            
            date_range = None
            if start_date and end_date:
                date_range = (start_date, end_date)
            
            # 先按条件查询
            records = self.get_records(conditions=conditions, 
                                      date_range=date_range,
                                      limit=limit)
            
            # 如果有关键词，进一步筛选
            if keywords and records:
                keywords_lower = keywords.lower()
                filtered_records = []
                for record in records:
                    # 在多个字段中搜索关键词
                    search_fields = ['name', 'advisor', 'equipment', 'remark', 'contact']
                    found = any(
                        keywords_lower in str(record.get(field, '')).lower()
                        for field in search_fields
                    )
                    if found:
                        filtered_records.append(record)
                records = filtered_records
            
            return records
            
        except Exception as e:
            logger.error(f"搜索记录失败: {e}")
            return []
