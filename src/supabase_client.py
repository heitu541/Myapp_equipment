# src/supabase_client.py - 修复版本
import logging
import streamlit as st

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Supabase客户端封装类"""
    
    def __init__(self):
        self.client = None
        
        try:
            # 检查secrets
            if not hasattr(st, 'secrets'):
                raise ValueError("Streamlit secrets未初始化")
                
            if "SUPABASE_URL" not in st.secrets or "SUPABASE_KEY" not in st.secrets:
                raise ValueError("缺少Supabase配置")
            
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
            
            # 导入并创建客户端
            from supabase import create_client
            self.client = create_client(url, key)
            
            logger.info("✅ Supabase连接成功")
            
        except Exception as e:
            logger.error(f"Supabase客户端初始化失败: {e}")
            self.client = None
    
    def insert(self, table: str, data: dict):
        """插入数据"""
        if not self.client:
            return None
        try:
            response = self.client.table(table).insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"插入失败: {e}")
            return None
    
    def update(self, table: str, data: dict, record_id: int):
        """更新数据"""
        if not self.client:
            return None
        try:
            response = self.client.table(table).update(data).eq('id', record_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"更新失败: {e}")
            return None
    
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
    
    def select(self, table: str, conditions: dict = None, order_by: str = None, limit: int = None):
        """查询数据"""
        if not self.client:
            return []
        
        try:
            query = self.client.table(table).select("*")
            
            if conditions:
                for key, value in conditions.items():
                    if value is not None:
                        query = query.eq(key, value)
            
            # 修复排序处理
            if order_by:
                # 解析排序参数
                parts = order_by.strip().split()
                if len(parts) >= 1:
                    field = parts[0]
                    # 默认降序，除非明确指定ASC
                    desc = True
                    if len(parts) >= 2 and parts[1].upper() == 'ASC':
                        desc = False
                    query = query.order(field, desc=desc)
            
            if limit:
                query = query.limit(limit)
            
            response = query.execute()
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"查询失败: {e}")
            return []
