# app.py - 优化版本
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import time
import hashlib
import re
import sys
import os
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== 路径设置 ====================
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')

# 添加src到路径
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# ==================== 初始化模块 ====================
# 在 init_managers() 函数之前添加这个函数
def load_record_for_editing(record_id: int):
    """加载记录到编辑表单"""
    try:
        # 获取完整记录数据并填充表单
        record = st.session_state.db_manager.get_record_by_id(record_id)
        if record:
            # 解析测试时间
            test_time = record.get('test_time', '')
            start_time = '08:00'
            end_time = '09:00'
            if test_time and '-' in test_time:
                try:
                    times = test_time.split('-')
                    start_time = times[0].strip()
                    end_time = times[1].strip() if len(times) > 1 else '09:00'
                except:
                    pass
            
            # 处理日期
            test_date_value = record.get('test_date', date.today())
            if isinstance(test_date_value, str):
                try:
                    test_date_value = datetime.strptime(test_date_value, '%Y-%m-%d').date()
                except:
                    test_date_value = date.today()
            
            # 填充表单数据
            st.session_state.form_data = {
                'equipment': record.get('equipment', ''),
                'test_date': test_date_value,
                'name': record.get('name', ''),
                'contact': record.get('contact', ''),
                'advisor': record.get('advisor', ''),
                'machine_hours': record.get('machine_hours', 0.0),
                'cost': record.get('cost', 0),
                'remark': record.get('remark', ''),
                'start_time': start_time,
                'end_time': end_time
            }
            
            # 设置编辑模式并跳转
            st.session_state.current_edit_id = record_id
            st.session_state.menu = "📝 登记记录"
            st.rerun()
        else:
            st.error("无法获取记录数据")
    except Exception as e:
        logger.error(f"加载编辑记录失败: {e}")
        st.error(f"加载记录失败：{str(e)}")
def init_managers():
    """初始化管理模块"""
    try:
        # 尝试导入模块
        from supabase_manager import SupabaseManager
        from config_manager import ConfigManager
        
        # 创建实例
        config_manager = ConfigManager()
        db_manager = SupabaseManager()
        
        logger.info("模块导入成功")
        return config_manager, db_manager
        
    except ImportError as e:
        logger.error(f"导入模块失败: {e}")
        st.error(f"模块导入失败: {e}")
        
        # 定义模拟类
        class MockConfigManager:
            def get_default_password_hash(self):
                return hash_password("9999")
        
        class MockSupabaseManager:
            def __init__(self):
                self.records = []
                self.next_id = 1
                logger.warning("使用模拟数据模式")
            
            def save_record(self, data, record_id=None):
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if record_id:
                    for i, r in enumerate(self.records):
                        if r['id'] == record_id:
                            self.records[i] = {**data, 'id': record_id, 
                                              'register_datetime': r.get('register_datetime', now), 
                                              'last_modified': now}
                            return True
                    return False
                else:
                    self.records.append({**data, 'id': self.next_id, 
                                        'register_datetime': now, 
                                        'last_modified': now})
                    self.next_id += 1
                    return True
            
            def delete_record(self, record_id):
                self.records = [r for r in self.records if r['id'] != record_id]
                return True
            
            def get_record_by_id(self, record_id):
                for r in self.records:
                    if r['id'] == record_id:
                        return r
                return None
            
            def get_records(self, limit=200):
                return self.records[:limit]
            
            def get_setting(self, key, default=None):
                if key == "admin_password_hash":
                    return hash_password("9999")
                return default
            
            def set_setting(self, key, value):
                return True
        
        return MockConfigManager(), MockSupabaseManager()

# 密码哈希函数
def hash_password(pwd: str) -> str:
    """计算密码的SHA256哈希值"""
    return hashlib.sha256(pwd.encode('utf-8')).hexdigest()

# ==================== 初始化Session State ====================
def init_session_state():
    """初始化Session State"""
    default_state = {
        'is_authenticated': False,
        'current_edit_id': None,
        'menu': "📝 查看记录",
        'form_data': {
            'equipment': '',
            'test_date': date.today(),
            'name': '',
            'contact': '',
            'advisor': '',
            'machine_hours': 0.0,
            'cost': 0,
            'remark': '',
            'start_time': '08:00',
            'end_time': '09:00'
        }
    }
    
    for key, value in default_state.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="仪器使用系统",
    page_icon="favicon.ico",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 工具函数 ====================
def verify_password(password: str) -> bool:
    """验证密码"""
    try:
        correct_hash = st.session_state.db_manager.get_setting(
            "admin_password_hash", 
            st.session_state.config_manager.get_default_password_hash()
        )
        return hash_password(password) == correct_hash
    except Exception as e:
        logger.error(f"密码验证失败: {e}")
        return hash_password(password) == hash_password("9999")

def show_password_dialog(action_name: str = "此操作") -> bool:
    # 检查是否已经验证过
    if st.session_state.is_authenticated:
        return True
    
    # 临时存储当前菜单状态
    original_menu = st.session_state.menu if 'menu' in st.session_state else "📋 查看记录"
    
    with st.form(f"password_verification_{action_name}"):
        st.warning(f"需要验证管理员密码才能{action_name}")
        password = st.text_input("请输入管理员密码", type="password", key=f"pwd_{action_name}")
        submitted = st.form_submit_button("验证")
        
        if submitted:
            if verify_password(password):
                st.session_state.is_authenticated = True
                st.success("验证成功！")
                # 如果是登记记录，设置菜单状态
                if action_name == "登记记录":
                    st.session_state.menu = "📝 登记记录"
                time.sleep(0.5)
                st.rerun()  # 这里添加 rerun
                return True
            else:
                st.error("密码错误！")
                return False
    
    # 如果显示对话框但未提交，返回False
    return False
# ==================== 表单组件 ====================
def show_records_table():
    """显示记录表格 - 优化版本，默认显示近7天记录"""
    st.header("📋 登记记录")
    
    # 初始化变量
    df_display = pd.DataFrame()  # 确保 df_display 始终被定义
    full_records = []
    
    # 初始化日期变量
    start_date = None
    end_date = None
    
    # 搜索过滤区域
    with st.expander("🔍 搜索过滤", expanded=False):
        # 快速筛选时间段
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # 添加快速时间筛选选项
            time_filter = st.selectbox(
                "快速筛选",
                ["近7天", "近30天", "自定义", "全部"],
                index=0
            )
        
        with col2:
            search_name = st.text_input("搜索姓名", placeholder="输入姓名关键字")
        with col3:
            search_equipment = st.text_input("搜索设备", placeholder="输入设备名称")
        with col4:
            search_advisor = st.text_input("搜索领导", placeholder="输入领导姓名")
        
        # 根据选择设置日期
        if time_filter == "自定义":
            col_date1, col_date2 = st.columns(2)
            with col_date1:
                start_date = st.date_input("开始日期", 
                                        value=date.today() - timedelta(days=30),
                                        max_value=date.today())
            with col_date2:
                end_date = st.date_input("结束日期", 
                                    value=date.today(),
                                    max_value=date.today())
        elif time_filter == "近7天":
            start_date = date.today() - timedelta(days=7)
            end_date = date.today()
        elif time_filter == "近30天":
            start_date = date.today() - timedelta(days=30)
            end_date = date.today()
        # "全部"时不设置日期，保持为None
    
    # 刷新按钮
    if st.button("🔄 刷新数据", use_container_width=True):
        st.rerun()
    
    try:
        # 构建查询条件
        conditions = {}
        if search_name:
            conditions['name'] = search_name
        if search_equipment:
            conditions['equipment'] = search_equipment
        if search_advisor:
            conditions['advisor'] = search_advisor
        
        # 设置日期范围
        date_range = None
        if start_date and end_date:
            date_range = (start_date.isoformat(), end_date.isoformat())
        
        # 获取记录
        with st.spinner("正在加载数据..."):
            records = st.session_state.db_manager.get_records_as_tuples(
                conditions=conditions if conditions else None,
                date_range=date_range,
                date_field="register_datetime",
                order_by="test_date DESC, id DESC",
                limit=500
            )
        
        if not records:
            st.info("📭 暂无记录")
            return
        
        # 创建显示用的DataFrame
        display_fields = ['登记时间', '测试日期', '测试时间', '姓名', '联系方式', '领导', '实验设备']
        
        display_data = []
        for record in records:
            record_id = record[0]  # ID
            display_tuple = (
                record[1],  # 登记时间
                record[2],  # 测试日期
                record[3],  # 测试时间
                record[4],  # 姓名
                record[5] if record[5] else "-",  # 联系方式
                record[6] if record[6] else "-",  # 领导
                record[7] if record[7] else "-",  # 实验设备
            )
            display_data.append(display_tuple)
            full_records.append((record_id, record))
        
        df_display = pd.DataFrame(display_data, columns=display_fields)
        
        # 显示当前筛选条件
        filter_info = []
        if time_filter:
            if time_filter == "自定义" and start_date and end_date:
                filter_info.append(f"时间范围: {start_date} 至 {end_date}")
            elif time_filter != "全部":
                filter_info.append(f"时间范围: {time_filter}")
        if search_name:
            filter_info.append(f"姓名包含: {search_name}")
        if search_equipment:
            filter_info.append(f"设备包含: {search_equipment}")
        if search_advisor:
            filter_info.append(f"领导包含: {search_advisor}")
        
        if filter_info:
            st.caption("📌 " + " | ".join(filter_info))
        
        # 显示表格
        st.subheader("📋 记录列表")
        
        # 格式化日期时间显示
        def format_datetime(dt_str):
            if not dt_str:
                return "-"
            try:
                if 'T' in dt_str:
                    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                    return dt.strftime("%Y-%m-%d %H:%M")
                else:
                    return dt_str
            except:
                return dt_str
        
        # 应用格式化
        if not df_display.empty:
            df_display['登记时间'] = df_display['登记时间'].apply(format_datetime)
            df_display['测试日期'] = pd.to_datetime(df_display['测试日期']).dt.strftime('%Y-%m-%d')
        
        # 显示表格
        df_display_with_index = df_display.reset_index(drop=True)
        df_display_with_index.index = df_display_with_index.index + 1
        
        st.dataframe(
            df_display_with_index,
            use_container_width=True,
            hide_index=False,
            column_config={
                "登记时间": st.column_config.DatetimeColumn("登记时间", format="YYYY-MM-DD HH:mm"),
                "测试日期": st.column_config.DateColumn("测试日期", format="YYYY-MM-DD"),
                "测试时间": st.column_config.TextColumn("测试时间"),
                "姓名": st.column_config.TextColumn("姓名", width="medium"),
                "联系方式": st.column_config.TextColumn("联系方式", width="medium"),
                "领导": st.column_config.TextColumn("领导", width="medium"),
                "实验设备": st.column_config.TextColumn("实验设备", width="large"),
            },
            height=400
        )
        
        st.caption(f"显示 {len(df_display)} 条记录")
        
        # 记录详情和操作区域
        st.subheader("🔍 记录详情")
        
        if not df_display.empty:
            # 选择记录查看详情
            selected_idx = st.selectbox(
                "选择记录查看详情或操作",
                range(len(df_display)),
                format_func=lambda idx: f"{df_display.iloc[idx]['姓名']} - {df_display.iloc[idx]['实验设备']} ({df_display.iloc[idx]['测试日期']})",
                key="record_selector"
            )
            
            if selected_idx is not None:
                # 获取对应的完整记录
                record_id, full_record_tuple = full_records[selected_idx]
                selected_display_record = df_display.iloc[selected_idx]
                
                # 创建两个选项卡：查看和编辑
                tab1, tab2 = st.tabs(["📋 查看详情", "✏️ 编辑记录"])
                
                with tab1:
                    # 显示详情卡片
                    with st.container(border=True):
                        col1, col2 = st.columns([1, 2])
                        
                        with col1:
                            st.markdown("**基本信息**")
                            st.write(f"**姓名**: {selected_display_record['姓名']}")
                            st.write(f"**领导**: {selected_display_record['领导']}")
                            st.write(f"**联系方式**: {selected_display_record['联系方式']}")
                            st.write(f"**测试日期**: {selected_display_record['测试日期']}")
                            
                        with col2:
                            st.markdown("**使用信息**")
                            st.write(f"**实验设备**: {selected_display_record['实验设备']}")
                            st.write(f"**测试时间**: {selected_display_record['测试时间']}")
                            st.write(f"**登记时间**: {selected_display_record['登记时间']}")
                            st.write(f"**机时**: {full_record_tuple[8]:.1f} 小时")
                            st.write(f"**费用**: {full_record_tuple[9]} 元")
                            if full_record_tuple[10]:  # 备注
                                st.write(f"**备注**: {full_record_tuple[10]}")
                    
                    # 操作按钮 - 只保留删除按钮
                    st.markdown("---")
                    if st.button("🗑️ 删除此记录", use_container_width=True, type="secondary", key=f"delete_{record_id}"):
                        # 检查是否已认证，如果未认证，先显示密码验证
                        if not st.session_state.is_authenticated:
                            # 直接在这里嵌入密码验证
                            with st.form(f"delete_auth_inline_{record_id}"):
                                st.warning("需要验证管理员密码才能删除记录")
                                password = st.text_input("请输入管理员密码", type="password", 
                                                       key=f"delete_pwd_inline_{record_id}")
                                submitted = st.form_submit_button("验证")
                                
                                if submitted:
                                    if verify_password(password):
                                        st.session_state.is_authenticated = True
                                        st.success("验证成功！现在可以删除记录")
                                        # 重新渲染以显示删除确认对话框
                                        st.rerun()
                                    else:
                                        st.error("密码错误！")
                        else:
                            # 已认证，显示删除确认对话框
                            delete_record(record_id)
                
                with tab2:
                    # 内嵌编辑表单
                    if not st.session_state.is_authenticated:
                        # 先要求密码验证
                        with st.form(f"verify_edit_tab_{record_id}"):
                            st.info("🔐 需要管理员权限才能编辑记录")
                            password = st.text_input("请输入管理员密码", type="password")
                            submitted = st.form_submit_button("验证")
                            
                            if submitted:
                                if verify_password(password):
                                    st.session_state.is_authenticated = True
                                    st.success("✅ 验证成功！现在可以编辑记录")
                                    st.rerun()
                                else:
                                    st.error("❌ 密码错误！")
                    else:
                        # 显示编辑表单
                        st.info(f"✏️ 正在编辑记录 ID: {record_id}")
                        
                        # 从记录中提取数据
                        record = st.session_state.db_manager.get_record_by_id(record_id)
                        if record:
                            # 解析测试时间
                            test_time = record.get('test_time', '')
                            start_time = '08:00'
                            end_time = '09:00'
                            if test_time and '-' in test_time:
                                try:
                                    times = test_time.split('-')
                                    start_time = times[0].strip()
                                    end_time = times[1].strip() if len(times) > 1 else '09:00'
                                except:
                                    pass
                            
                            # 处理日期
                            test_date_value = record.get('test_date', date.today())
                            if isinstance(test_date_value, str):
                                try:
                                    test_date_value = datetime.strptime(test_date_value, '%Y-%m-%d').date()
                                except:
                                    test_date_value = date.today()
                            
                            # 编辑表单
                            with st.form(f"edit_form_{record_id}"):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    # 修改设备输入为下拉选择
                                    from utils import Utils
                                    preset_devices = Utils.get_preset_equipment()
                                    
                                    if not preset_devices:
                                        st.error("⚠️ 没有可用的设备，请在设备管理中添加设备")
                                        equipment = ""
                                    else:
                                        # 直接选择预设设备
                                        current_equipment = record.get('equipment', '')
                                        equipment = st.selectbox(
                                            "实验设备 *",
                                            options=preset_devices,
                                            index=0 if not current_equipment else (
                                                preset_devices.index(current_equipment) if current_equipment in preset_devices else 0
                                            ),
                                            help="请选择实验设备"
                                        )
                                    
                                    test_date = st.date_input("测试日期 *", value=test_date_value)
                                    
                                    name = st.text_input("姓名 *", 
                                                        value=record.get('name', ''),
                                                        placeholder="请输入姓名")
                                    contact = st.text_input("联系方式", 
                                                        value=record.get('contact', ''),
                                                        placeholder="电话/邮箱")
                                
                                with col2:
                                    advisor = st.text_input("领导", 
                                                        value=record.get('advisor', ''),
                                                        placeholder="领导姓名")
                                    
                                    # 时间处理 - 修复step参数
                                    time_col1, time_col2 = st.columns(2)
                                    with time_col1:
                                        try:
                                            start_time_val = datetime.strptime(start_time, "%H:%M").time()
                                        except:
                                            start_time_val = datetime.strptime("08:00", "%H:%M").time()
                                        # 将step参数明确转换为整数
                                        start_time_input = st.time_input("开始时间", value=start_time_val, step=900)
                                    
                                    with time_col2:
                                        try:
                                            end_time_val = datetime.strptime(end_time, "%H:%M").time()
                                        except:
                                            end_time_val = datetime.strptime("09:00", "%H:%M").time()
                                        # 将step参数明确转换为整数
                                        end_time_input = st.time_input("结束时间", value=end_time_val, step=900)
                                    
                                    # 修复机器小时数的格式化
                                    machine_hours_val = record.get('machine_hours', 0.0)
                                    if machine_hours_val is None:
                                        machine_hours_val = 0.0
                                    machine_hours = st.number_input("机时（小时）", 
                                                                min_value=0.0, 
                                                                max_value=24.0,
                                                                value=float(machine_hours_val), 
                                                                step=0.5, 
                                                                format="%.1f")
                                    
                                    # 修复费用的格式化
                                    cost_val = record.get('cost', 0)
                                    if cost_val is None:
                                        cost_val = 0
                                    cost = st.number_input("费用（元）", 
                                                        min_value=0, 
                                                        value=int(cost_val), 
                                                        step=1)
                                
                                remark = st.text_area("备注", 
                                                    value=record.get('remark', ''), 
                                                    height=100,
                                                    placeholder="请输入备注信息")
                                
                                # 表单验证
                                def validate_edit_form():
                                    errors = []
                                    if not equipment.strip():
                                        errors.append("实验设备为必填项")
                                    if not name.strip():
                                        errors.append("姓名为必填项")
                                    if start_time_input >= end_time_input:
                                        errors.append("结束时间必须晚于开始时间")
                                    return errors
                                
                                col_save, col_cancel = st.columns(2)
                                with col_save:
                                    # 主提交按钮
                                    submitted_form = st.form_submit_button("💾 保存修改", type="primary", use_container_width=True)
                                
                                with col_cancel:
                                    # 取消按钮 - 必须放在表单内
                                    cancel_button = st.form_submit_button("❌ 取消编辑", use_container_width=True)
                                
                                # 处理提交
                                if submitted_form:
                                    errors = validate_edit_form()
                                    if errors:
                                        for error in errors:
                                            st.error(error)
                                    else:
                                        try:
                                            # 组合时间段
                                            test_time_str = f"{start_time_input.strftime('%H:%M')}-{end_time_input.strftime('%H:%M')}"
                                            
                                            record_data = {
                                                'test_date': test_date.isoformat(),
                                                'test_time': test_time_str,
                                                'name': name,
                                                'contact': contact,
                                                'advisor': advisor,
                                                'equipment': equipment,
                                                'machine_hours': float(machine_hours),
                                                'cost': int(cost),
                                                'remark': remark
                                            }
                                            
                                            success = st.session_state.db_manager.save_record(record_data, record_id)
                                            
                                            if success:
                                                # 显示成功消息
                                                success_msg = st.success("✅ 记录更新成功！页面将在2秒后刷新...")
                                                time.sleep(2)
                                                success_msg.empty()  # 清除消息
                                                st.rerun()
                                            else:
                                                error_msg = st.error("❌ 更新失败，请检查数据格式")
                                                time.sleep(2)
                                                error_msg.empty()  # 清除消息
                                                st.stop()
                                                
                                        except Exception as e:
                                            logger.error(f"更新记录失败: {e}")
                                            error_msg = st.error(f"❌ 更新失败：{str(e)}")
                                            time.sleep(2)
                                            error_msg.empty()  # 清除消息
                                            st.stop()
                                if cancel_button:
                                    st.info("编辑已取消")
                                    time.sleep(0.5)
                                    st.rerun()
                        else:
                            st.error("无法加载记录数据")
        
    except Exception as e:
        logger.error(f"加载数据失败: {e}")
        st.error(f"加载数据失败：{str(e)}")
def save_record(**kwargs):
    """保存记录"""
    try:
        # 组合时间段
        test_time = f"{kwargs['start_time']}-{kwargs['end_time']}"
        
        record_data = {
            'test_date': kwargs['test_date'],
            'test_time': test_time,
            'name': kwargs['name'],
            'contact': kwargs['contact'],
            'advisor': kwargs['advisor'],
            'equipment': kwargs['equipment'],
            'machine_hours': kwargs['machine_hours'],
            'cost': kwargs['cost'],
            'remark': kwargs['remark']
        }
        
        if st.session_state.current_edit_id:
            success = st.session_state.db_manager.save_record(
                record_data, 
                st.session_state.current_edit_id
            )
            action = "更新"
        else:
            success = st.session_state.db_manager.save_record(record_data)
            action = "新增"
        
        if success:
            # 显示成功消息
            success_msg = st.success(f"✅ 记录{action}成功！页面将在2秒后刷新...")
            clear_form()
            time.sleep(2)
            success_msg.empty()  # 清除消息
            st.rerun()
        else:
            error_msg = st.error("❌ 保存失败，请检查数据格式")
            time.sleep(2)
            error_msg.empty()  # 清除消息
            st.stop()
            
    except Exception as e:
        logger.error(f"保存记录失败: {e}")
        st.error(f"❌ 保存失败：{str(e)}")

def clear_form():
    """清空表单"""
    st.session_state.form_data = {
        'equipment': '',
        'test_date': date.today(),
        'name': '',
        'contact': '',
        'advisor': '',
        'machine_hours': 0.0,
        'cost': 0,
        'remark': '',
        'start_time': '08:00',
        'end_time': '09:00'
    }
    st.session_state.current_edit_id = None
# ==================== 登记表单组件 ====================
def show_registration_form():
    """显示登记表单"""
    # 标题
    if st.session_state.current_edit_id:
        st.header(f"✏️ 编辑记录 (ID: {st.session_state.current_edit_id})")
    else:
        st.header("📝 登记新记录")
    
    # 如果是编辑模式，显示提示
    if st.session_state.current_edit_id:
        with st.container(border=True):
            col_info, col_cancel = st.columns([3, 1])
            with col_info:
                st.warning(f"⚠️ 正在编辑记录 ID: {st.session_state.current_edit_id}")
            with col_cancel:
                if st.button("❌ 取消编辑", use_container_width=True):
                    clear_form()
                    st.session_state.menu = "📋 查看记录"
                    st.rerun()
    
    # 表单布局
    col1, col2 = st.columns(2)
    
    with col1:
        # 修改这里：从下拉选择改为直接选择预设设备
        from utils import Utils
        preset_devices = Utils.get_preset_equipment()
        
        if not preset_devices:
            st.error("⚠️ 没有可用的设备，请在设备管理中添加设备")
            equipment = ""
        else:
            # 直接选择设备，不再有自定义选项
            equipment = st.selectbox(
                "实验设备 *",
                options=preset_devices,
                index=0,
                help="请选择实验设备"
            )
        
        # 安全处理日期
        try:
            test_date_value = st.session_state.form_data.get('test_date')
            if isinstance(test_date_value, date):
                test_date = test_date_value
            elif isinstance(test_date_value, str):
                test_date = datetime.strptime(test_date_value, '%Y-%m-%d').date()
            else:
                test_date = date.today()
        except:
            test_date = date.today()
            
        test_date = st.date_input("测试日期 *", value=test_date)
        
        name = st.text_input("姓名 *", 
                            value=st.session_state.form_data.get('name', ''),
                            placeholder="请输入姓名")
        contact = st.text_input("联系方式", 
                               value=st.session_state.form_data.get('contact', ''),
                               placeholder="电话/邮箱")
    
    with col2:
        advisor = st.text_input("领导", 
                               value=st.session_state.form_data.get('advisor', ''),
                               placeholder="领导姓名")
        # 时间处理
        time_col1, time_col2 = st.columns(2)
        with time_col1:
            try:
                start_time_str = st.session_state.form_data.get('start_time', '08:00')
                if isinstance(start_time_str, str):
                    start_time_val = datetime.strptime(start_time_str, "%H:%M").time()
                else:
                    start_time_val = datetime.strptime("08:00", "%H:%M").time()
            except:
                start_time_val = datetime.strptime("08:00", "%H:%M").time()
            start_time = st.time_input("开始时间", value=start_time_val, step=1800) 

        with time_col2:
            try:
                end_time_str = st.session_state.form_data.get('end_time', '09:00')
                if isinstance(end_time_str, str):
                    end_time_val = datetime.strptime(end_time_str, "%H:%M").time()
                else:
                    end_time_val = datetime.strptime("09:00", "%H:%M").time()
            except:
                end_time_val = datetime.strptime("09:00", "%H:%M").time()
            end_time = st.time_input("结束时间", value=end_time_val, step=1800)      
        # 安全处理数字字段
        try:
            machine_hours_value = st.session_state.form_data.get('machine_hours', 0.0)
            machine_hours = float(machine_hours_value)
        except:
            machine_hours = 0.0
            
        machine_hours = st.number_input("机时（小时）", 
                                       min_value=0.0, 
                                       max_value=24.0,
                                       value=machine_hours, 
                                       step=0.5, 
                                       format="%.1f")
        
        try:
            cost_value = st.session_state.form_data.get('cost', 0)
            cost = int(cost_value)
        except:
            cost = 0
            
        cost = st.number_input("费用（元）", 
                              min_value=0, 
                              value=cost, 
                              step=1)
    
    # 备注
    remark = st.text_area("备注", 
                         value=st.session_state.form_data.get('remark', ''), 
                         height=100,
                         placeholder="请输入备注信息")
    
    # 表单验证
    def validate_form():
        errors = []
        if not equipment:  # 直接检查设备是否为空
            errors.append("请选择实验设备")
        if not name.strip():
            errors.append("姓名为必填项")
        if start_time >= end_time:
            errors.append("结束时间必须晚于开始时间")
        return errors
    
    # 按钮区域
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        button_text = "💾 更新记录" if st.session_state.current_edit_id else "💾 保存记录"
        if st.button(button_text, type="primary", use_container_width=True):
            errors = validate_form()
            if errors:
                for error in errors:
                    st.error(error)
            else:
                try:
                    # 组合时间段
                    test_time = f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"
                    
                    record_data = {
                        'test_date': test_date.isoformat(),
                        'test_time': test_time,
                        'name': name,
                        'contact': contact,
                        'advisor': advisor,
                        'equipment': equipment,
                        'machine_hours': machine_hours,
                        'cost': cost,
                        'remark': remark
                    }
                    
                    if st.session_state.current_edit_id:
                        success = st.session_state.db_manager.save_record(
                            record_data, 
                            st.session_state.current_edit_id
                        )
                        action = "更新"
                    else:
                        success = st.session_state.db_manager.save_record(record_data)
                        action = "新增"
                    
                    if success:
                        # 显示成功消息并清空表单
                        success_container = st.empty()
                        success_container.success(f"✅ 记录{action}成功！页面将在2秒后刷新...")
                        clear_form()
                        time.sleep(2)
                        success_container.empty()
                        # 返回到查看记录页面
                        if st.session_state.current_edit_id:
                            st.session_state.current_edit_id = None
                            st.session_state.menu = "📋 查看记录"
                        st.rerun()
                    else:
                        error_container = st.empty()
                        error_container.error("❌ 保存失败，请检查数据格式")
                        time.sleep(2)
                        error_container.empty()
                        
                except Exception as e:
                    logger.error(f"保存记录失败: {e}")
                    error_container = st.empty()
                    error_container.error(f"❌ 保存失败：{str(e)}")
                    time.sleep(2)
                    error_container.empty()
    
    with col_btn2:
        if st.button("🧹 清空表单", use_container_width=True):
            clear_form()
            st.rerun()
    
    with col_btn3:
        if st.session_state.current_edit_id:
            if st.button("📋 返回查看", use_container_width=True):
                st.session_state.current_edit_id = None
                st.session_state.menu = "📋 查看记录"
                st.rerun()

def delete_record(record_id: int):
    """删除记录"""
    # 先检查密码验证
    if not st.session_state.is_authenticated:
        # 显示密码验证对话框
        with st.form(f"delete_auth_form_{record_id}"):
            st.warning("需要验证管理员密码才能删除记录")
            password = st.text_input("请输入管理员密码", type="password", 
                                   key=f"delete_pwd_{record_id}")
            submitted = st.form_submit_button("验证")
            
            if submitted:
                if verify_password(password):
                    st.session_state.is_authenticated = True
                    success_msg = st.success("验证成功！")
                    time.sleep(0.5)
                    success_msg.empty()
                    st.rerun()  # 重新加载页面以进入删除确认流程
                else:
                    st.error("密码错误！")
        return  # 如果未验证，不继续执行删除逻辑
    
    try:
        # 确认对话框
        with st.form(f"confirm_delete_{record_id}"):
            st.warning("⚠️ 确定要删除这条记录吗？此操作不可恢复！")
            
            col1, col2 = st.columns(2)
            with col1:
                confirm = st.form_submit_button("✅ 确认删除", type="primary", use_container_width=True)
            with col2:
                cancel = st.form_submit_button("❌ 取消", use_container_width=True)
            
            if confirm:
                try:
                    if st.session_state.db_manager.delete_record(record_id):
                        # 显示成功消息
                        success_container = st.empty()
                        success_container.success("✅ 记录删除成功！页面将在2秒后刷新...")
                        time.sleep(2)
                        success_container.empty()
                        # 清除选择状态，避免显示已删除的记录
                        if 'record_selector' in st.session_state:
                            st.session_state.record_selector = 0
                        st.session_state.is_authenticated = False  # 删除后需要重新验证
                        st.rerun()
                    else:
                        error_container = st.empty()
                        error_container.error("❌ 删除失败，请重试")
                        time.sleep(2)
                        error_container.empty()
                except Exception as e:
                    logger.error(f"删除记录失败: {e}")
                    error_container = st.empty()
                    error_container.error(f"❌ 删除失败：{str(e)}")
                    time.sleep(2)
                    error_container.empty()
            
            if cancel:
                st.info("删除操作已取消")
                time.sleep(0.5)
                st.rerun()
    except Exception as e:
        logger.error(f"删除记录失败: {e}")
        st.error(f"删除记录失败：{str(e)}")

# ==================== 修改密码组件 ====================
def show_change_password():
    """显示修改密码页面"""
    st.header("🔑 修改管理员密码")
    
    if not st.session_state.is_authenticated:
        if not show_password_dialog("修改密码"):
            return
    
    with st.form("change_password_form"):
        st.subheader("设置新密码")
        
        col1, col2 = st.columns(2)
        with col1:
            new_password1 = st.text_input("新密码", type="password", 
                                         help="密码长度至少4位")
        with col2:
            new_password2 = st.text_input("确认新密码", type="password")
        
        submitted = st.form_submit_button("💾 保存新密码", type="primary")
        
        if submitted:
            # 验证密码
            if not new_password1 or not new_password2:
                st.error("请输入新密码")
            elif len(new_password1) < 4:
                st.error("密码长度至少4位")
            elif new_password1 != new_password2:
                st.error("两次输入的密码不一致")
            else:
                try:
                    new_hash = hash_password(new_password1)
                    if st.session_state.db_manager.set_setting("admin_password_hash", new_hash):
                        # 显示成功消息
                        success_msg = st.success("✅ 密码已更新，页面将在2秒后刷新...")
                        st.session_state.is_authenticated = False
                        time.sleep(2)
                        success_msg.empty()  # 清除消息
                        st.rerun()
                    else:
                        error_msg = st.error("❌ 密码更新失败")
                        time.sleep(2)
                        error_msg.empty()  # 清除消息
                        st.stop()
                except Exception as e:
                    error_msg = st.error(f"❌ 密码更新失败：{str(e)}")
                    time.sleep(2)
                    error_msg.empty()  # 清除消息
                    st.stop()

# ==================== 侧边栏 ====================
def show_sidebar():
    """显示侧边栏"""
    with st.sidebar:
        # 添加自定义Logo和标题
        col_logo, col_title = st.columns([1, 3])
        
        with col_logo:
            # 加载并显示自定义Logo
            try:
                # 确保logo.png文件存在
                st.image("logo.png", width=50)  # 调整宽度以适应您的Logo
            except FileNotFoundError:
                # 如果找不到Logo文件，显示默认图标
                st.markdown("🔬")
        
        with col_title:
            st.title("仪器使用系统")
        
        st.markdown("---")
        
        # 改为4个功能按钮，不再使用下拉菜单
        st.subheader("📋 功能菜单")
        
        # 查看记录按钮
        if st.button("📋 查看记录", use_container_width=True, type="primary" if st.session_state.menu == "📋 查看记录" else "secondary"):
            st.session_state.menu = "📋 查看记录"
            st.session_state.current_edit_id = None
            st.rerun()
        
        # 登记记录按钮（需要密码验证）
        if st.button("📝 登记记录", use_container_width=True, type="primary" if st.session_state.menu == "📝 登记记录" else "secondary"):
            # 直接设置菜单状态，让main函数处理验证
            st.session_state.menu = "📝 登记记录"
            st.session_state.current_edit_id = None
            st.rerun()
        
        # 设备管理按钮
        if st.button("⚙️ 设备管理", use_container_width=True, type="primary" if st.session_state.menu == "⚙️ 设备管理" else "secondary"):
            st.session_state.menu = "⚙️ 设备管理"
            st.rerun()
        
        # 修改密码按钮
        if st.button("🔑 修改密码", use_container_width=True, type="primary" if st.session_state.menu == "🔑 修改密码" else "secondary"):
            st.session_state.menu = "🔑 修改密码"
            st.rerun()
        
        st.markdown("---")
        
        # 用户状态
        status = "管理员" if st.session_state.is_authenticated else "普通用户"
        st.caption(f"👤 当前用户: {status}")
        
        # 登出按钮
        if st.session_state.is_authenticated:
            if st.button("🚪 退出管理员", use_container_width=True):
                st.session_state.is_authenticated = False
                st.success("已退出管理员模式")
                time.sleep(0.5)
                st.rerun()
        
        st.markdown("---")
        
        # 系统信息
        try:
            records = st.session_state.db_manager.get_records(limit=5)
            st.caption(f"📊 最近记录数: {len(records)}")
        except:
            st.caption("📊 无法获取记录")
        
        st.caption(f"📅 系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
def show_edit_record_page(record_id: int):
    """显示编辑记录页面"""
    if not st.session_state.is_authenticated:
        if not show_password_dialog("编辑记录"):
            st.warning("需要管理员权限才能编辑记录")
            st.session_state.menu = "📋 查看记录"
            st.rerun()
            return
    
    # 加载记录数据
    record = st.session_state.db_manager.get_record_by_id(record_id)
    if not record:
        st.error("记录不存在")
        st.session_state.menu = "📋 查看记录"
        st.rerun()
        return
    
    st.header(f"✏️ 编辑记录 (ID: {record_id})")
    
    # 使用现有的登记表单组件，但预先填充数据
    # 解析测试时间
    test_time = record.get('test_time', '08:00-09:00')
    start_time = '08:00'
    end_time = '09:00'
    if test_time and '-' in test_time:
        try:
            times = test_time.split('-')
            start_time = times[0].strip()
            end_time = times[1].strip() if len(times) > 1 else '09:00'
        except:
            pass
    
    # 处理日期
    test_date_value = record.get('test_date', date.today())
    if isinstance(test_date_value, str):
        try:
            test_date_value = datetime.strptime(test_date_value, '%Y-%m-%d').date()
        except:
            test_date_value = date.today()
    
    # 设置表单数据
    st.session_state.form_data = {
        'equipment': record.get('equipment', ''),
        'test_date': test_date_value,
        'name': record.get('name', ''),
        'contact': record.get('contact', ''),
        'advisor': record.get('advisor', ''),
        'machine_hours': record.get('machine_hours', 0.0),
        'cost': record.get('cost', 0),
        'remark': record.get('remark', ''),
        'start_time': start_time,
        'end_time': end_time
    }
    
    st.session_state.current_edit_id = record_id
    
    # 显示登记表单（会自动使用 session_state 中的数据）
    show_registration_form()
    
    # 添加返回按钮
    if st.button("↩️ 返回查看页面", use_container_width=True):
        st.session_state.current_edit_id = None
        st.session_state.menu = "📋 查看记录"
        st.rerun()

# ==================== 设备管理组件 ====================
def show_equipment_management():
    """显示设备管理页面"""
    st.header("⚙️ 设备管理")
    
    # 先检查是否已认证
    if not st.session_state.is_authenticated:
        # 使用独立的验证表单
        with st.container():
            st.warning("需要验证管理员密码才能管理设备")
            
            # 创建验证表单
            with st.form("equipment_auth_form"):
                password = st.text_input("请输入管理员密码", type="password", 
                                       key="equipment_pwd")
                submitted = st.form_submit_button("验证")
                
                if submitted:
                    if verify_password(password):
                        st.session_state.is_authenticated = True
                        st.success("验证成功！")
                        time.sleep(0.5)  # 短暂延迟让用户看到成功消息
                        st.rerun()  # 立即重载
                    else:
                        st.error("密码错误！")
            
            # 如果未通过验证，不显示后续内容
            if not st.session_state.is_authenticated:
                return
    else:
        # 如果已认证，显示成功消息（短暂显示）
        if 'show_success_msg' not in st.session_state:
            st.success("✅ 验证成功！")
            st.session_state.show_success_msg = True
            # 设置定时器自动清除消息
            time.sleep(1)
            st.rerun()
    
    try:
        from utils import Utils
        
        # 获取当前预设设备
        current_devices = Utils.get_preset_equipment()
        
        # 清除可能存在的成功消息标志
        if 'show_success_msg' in st.session_state:
            del st.session_state.show_success_msg
        
        # 显示当前设备列表
        st.subheader("📋 当前预设设备列表")
        
        if not current_devices:
            st.info("暂无预设设备")
        else:
            # 使用session state管理删除状态
            delete_key = f"delete_confirm_{len(current_devices)}"
            if delete_key not in st.session_state:
                st.session_state[delete_key] = None
            
            for i, device in enumerate(current_devices, 1):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"{i}. {device}")
                with col2:
                    delete_btn_key = f"delete_btn_{i}"
                    if st.button(f"删除", key=delete_btn_key, use_container_width=True):
                        # 设置要删除的设备索引
                        st.session_state[delete_key] = i - 1
                        st.rerun()
            
            # 处理删除确认
            if st.session_state[delete_key] is not None:
                delete_index = st.session_state[delete_key]
                device_to_delete = current_devices[delete_index]
                
                with st.container(border=True):
                    st.warning(f"⚠️ 确定要删除设备 '{device_to_delete}' 吗？")
                    
                    col_confirm, col_cancel = st.columns(2)
                    with col_confirm:
                        confirm_key = f"confirm_delete_{delete_index}"
                        if st.button("确认删除", key=confirm_key, type="primary", use_container_width=True):
                            try:
                                # 删除设备
                                current_devices.pop(delete_index)
                                if Utils.save_preset_equipment(current_devices):
                                    # 清理session state
                                    st.session_state[delete_key] = None
                                    # 显示成功消息
                                    success_msg = st.success(f"✅ 已删除设备: {device_to_delete}，页面将在2秒后刷新...")
                                    time.sleep(2)
                                    success_msg.empty()
                                    st.rerun()
                                else:
                                    error_msg = st.error("❌ 删除失败")
                                    time.sleep(2)
                                    error_msg.empty()
                                    st.stop()
                            except Exception as e:
                                error_msg = st.error(f"❌ 删除失败：{str(e)}")
                                time.sleep(2)
                                error_msg.empty()
                                st.stop()
                    
                    with col_cancel:
                        cancel_key = f"cancel_delete_{delete_index}"
                        if st.button("取消", key=cancel_key, use_container_width=True):
                            # 清理session state
                            st.session_state[delete_key] = None
                            st.rerun()
        
        st.markdown("---")
        
        # 添加新设备
        st.subheader("➕ 添加新设备")
        
        # 使用session state来管理新设备输入
        if 'new_device_input' not in st.session_state:
            st.session_state.new_device_input = ""
        if 'add_device_submitted' not in st.session_state:
            st.session_state.add_device_submitted = False
        
        with st.form("add_equipment_form"):  # 移除 clear_on_submit=True
            new_device = st.text_input("设备名称", 
                                     value=st.session_state.new_device_input,
                                     placeholder="请输入实验设备名称",
                                     help="例如：扫描电子显微镜")
            
            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("💾 添加设备", use_container_width=True)
            with col2:
                clear_all_btn = st.form_submit_button("🗑️ 清空所有设备", 
                                                    use_container_width=True,
                                                    type="secondary")
            
            # 处理表单提交
            if submit:
                st.session_state.new_device_input = new_device
                st.session_state.add_device_submitted = True
                st.rerun()
            
            if clear_all_btn:
                # 设置清空标志
                if 'clear_all_confirm' not in st.session_state:
                    st.session_state.clear_all_confirm = False
                st.session_state.clear_all_confirm = True
                st.rerun()
        
        # 处理添加设备的逻辑（在表单外）
        if st.session_state.add_device_submitted:
            device_name = st.session_state.new_device_input.strip()
            st.session_state.add_device_submitted = False
            st.session_state.new_device_input = ""
            
            # 验证设备名称
            if not device_name:
                error_msg = st.error("❌ 请输入设备名称")
                time.sleep(2)
                error_msg.empty()
                st.stop()
            elif device_name in current_devices:
                warning_msg = st.warning(f"⚠️ 设备 '{device_name}' 已存在")
                time.sleep(2)
                warning_msg.empty()
                st.stop()
            else:
                try:
                    # 添加新设备
                    current_devices.append(device_name)
                    if Utils.save_preset_equipment(current_devices):
                        # 显示成功消息
                        success_msg = st.success(f"✅ 已添加设备: {device_name}，页面将在2秒后刷新...")
                        time.sleep(2)
                        success_msg.empty()
                        st.rerun()
                    else:
                        error_msg = st.error("❌ 添加失败，无法保存到配置文件")
                        time.sleep(2)
                        error_msg.empty()
                        st.stop()
                except Exception as e:
                    error_msg = st.error(f"❌ 添加失败：{str(e)}")
                    time.sleep(2)
                    error_msg.empty()
                    st.stop()
        
        # 处理清空所有设备的确认
        if st.session_state.get('clear_all_confirm', False):
            with st.container(border=True):
                st.warning("⚠️ 确定要清空所有预设设备吗？此操作不可恢复！")
                
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("确认清空", key="confirm_clear_all", type="primary", use_container_width=True):
                        try:
                            if Utils.save_preset_equipment([]):
                                # 清理session state
                                st.session_state.clear_all_confirm = False
                                # 显示成功消息
                                success_msg = st.success("✅ 已清空所有预设设备，页面将在2秒后刷新...")
                                time.sleep(2)
                                success_msg.empty()
                                st.rerun()
                            else:
                                error_msg = st.error("❌ 清空失败")
                                time.sleep(2)
                                error_msg.empty()
                                st.stop()
                        except Exception as e:
                            error_msg = st.error(f"❌ 清空失败：{str(e)}")
                            time.sleep(2)
                            error_msg.empty()
                            st.stop()
                
                with col_cancel:
                    if st.button("取消", key="cancel_clear_all", use_container_width=True):
                        st.session_state.clear_all_confirm = False
                        st.rerun()
        
        st.markdown("---")
        st.info("💡 **提示**: 添加的设备将在登记和编辑记录时以下拉菜单的形式显示，避免手动输入错误。")
        
    except Exception as e:
        logger.error(f"设备管理失败: {e}")
        st.error(f"设备管理失败：{str(e)}")

# ==================== 主函数 ====================
def main():
    """主函数"""
    # 初始化
    if 'config_manager' not in st.session_state or 'db_manager' not in st.session_state:
        st.session_state.config_manager, st.session_state.db_manager = init_managers()
    
    # 初始化session state - 设置默认显示查看记录
    init_session_state()
    
    # 默认显示查看记录
    if 'menu' not in st.session_state or not st.session_state.menu:
        st.session_state.menu = "📋 查看记录"
    
    # 显示侧边栏
    show_sidebar()
    
    # 显示主内容
    if st.session_state.menu == "📝 登记记录":
        # 如果未认证，先显示验证表单
        if not st.session_state.is_authenticated:
            st.header("📝 登记新记录")
            with st.form("register_auth_form"):
                st.warning("需要验证管理员密码才能登记记录")
                password = st.text_input("请输入管理员密码", type="password", 
                                       key="register_pwd")
                submitted = st.form_submit_button("验证")
                
                if submitted:
                    if verify_password(password):
                        st.session_state.is_authenticated = True
                        success_msg = st.success("验证成功！")
                        time.sleep(0.5)
                        success_msg.empty()
                        st.rerun()
                    else:
                        st.error("密码错误！")
            # 如果未验证，停止执行后续代码
            return
        
        # 已认证，显示登记表单
        show_registration_form()
        
    elif st.session_state.menu == "📋 查看记录":
        show_records_table()
    elif st.session_state.menu == "⚙️ 设备管理":
        show_equipment_management()
    elif st.session_state.menu == "🔑 修改密码":
        show_change_password()

# ==================== 运行应用 ====================
if __name__ == "__main__":
    main()
