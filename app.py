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
        'menu': "📋 查看记录",
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
    """显示记录表格 - 简洁两行布局"""
    st.header("📋 登记记录")
    
    # 搜索过滤区域
    with st.expander("🔍 搜索过滤", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            time_filter = st.selectbox(
                "快速筛选",
                ["近7天", "近30天", "自定义", "全部"],
                index=0
            )
        
        with col2:
            search_name = st.text_input("搜索姓名", placeholder="输入姓名关键字")
        with col3:
            # 改为下拉选择设备
            try:
                from utils import Utils
                preset_devices = Utils.get_preset_equipment()
                
                # 添加"全部设备"选项
                device_options = ["全部设备"] + preset_devices
                
                selected_device = st.selectbox(
                    "搜索设备",
                    options=device_options,
                    index=0,
                    help="请选择要筛选的设备"
                )
                
                # 如果不是"全部设备"，则设置搜索条件
                if selected_device != "全部设备":
                    search_equipment = selected_device
                else:
                    search_equipment = ""  # 空字符串表示不筛选
                    
            except Exception as e:
                logger.error(f"获取设备列表失败: {e}")
                search_equipment = st.text_input("搜索设备", placeholder="输入设备名称关键词")
                
        with col4:
            search_advisor = st.text_input("搜索领导", placeholder="输入领导姓名")
        
        # 自定义日期范围
        start_date = None
        end_date = None
        if time_filter == "自定义":
            col_date1, col_date2 = st.columns(2)
            with col_date1:
                start_date = st.date_input("开始日期", 
                                        value=date.today() - timedelta(days=30),
                                        max_value=date.today())
            with col_date2:
                # 结束日期可以设置未来日期
                end_date = st.date_input("结束日期", 
                                    value=date.today())
        elif time_filter == "近7天":
            # 开始日期是7天前，结束日期不限制（可以包括未来）
            start_date = date.today() - timedelta(days=7)
            end_date = None  # 设置为None，表示不限制结束日期
        elif time_filter == "近30天":
            # 开始日期是30天前，结束日期不限制（可以包括未来）
            start_date = date.today() - timedelta(days=30)
            end_date = None  # 设置为None，表示不限制结束日期
    
    # 刷新按钮
    col_refresh, col_stats = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 刷新", use_container_width=True):
            st.rerun()
    
    try:
        # 获取所有记录，然后在内存中进行模糊过滤
        with st.spinner("正在加载数据..."):
            records = st.session_state.db_manager.get_records_as_tuples(
                date_field="test_date",
                order_by="test_date DESC, id DESC",
                limit=500
            )
        
        if not records:
            st.info("📭 暂无记录")
            return
        
        # 应用模糊搜索过滤
        filtered_records = []
        for record in records:
            record_dict = {
                'id': record[0],
                'register_datetime': record[1],
                'test_date': record[2],
                'test_time': record[3],
                'name': record[4],
                'contact': record[5],
                'advisor': record[6],
                'equipment': record[7],
                'machine_hours': record[8],
                'cost': record[9],
                'remark': record[10]
            }
            
            # 姓名模糊匹配
            if search_name:
                if search_name.lower() not in str(record[4]).lower():
                    continue
            
            # 设备精确匹配（因为现在是选择，不是模糊搜索）
            if search_equipment:  # 只有当选择了具体设备时才筛选
                if search_equipment != record[7]:  # 精确匹配
                    continue
            
            # 领导模糊匹配
            if search_advisor:
                if search_advisor.lower() not in str(record[6]).lower():
                    continue
            
            # 日期范围过滤 - 修复逻辑
            if start_date:
                try:
                    record_date = datetime.strptime(record[2], '%Y-%m-%d').date()
                    # 只检查开始日期，不检查结束日期（允许未来日期）
                    if record_date < start_date:
                        continue
                    # 如果有结束日期限制，才检查结束日期
                    if end_date and record_date > end_date:
                        continue
                except:
                    continue
            
            filtered_records.append(record)
        
        records = filtered_records
        
        # 显示筛选信息
        filter_info = []
        if time_filter:
            if time_filter == "自定义" and start_date and end_date:
                filter_info.append(f"时间范围: {start_date} 至 {end_date}")
            elif time_filter == "近7天":
                filter_info.append(f"时间范围: 最近7天及未来")
            elif time_filter == "近30天":
                filter_info.append(f"时间范围: 最近30天及未来")
            elif time_filter != "全部":
                filter_info.append(f"时间范围: {time_filter}")
        if search_name:
            filter_info.append(f"姓名包含: {search_name}")
        if search_equipment:
            filter_info.append(f"设备: {search_equipment}")
        if search_advisor:
            filter_info.append(f"领导包含: {search_advisor}")
        
        if filter_info:
            st.caption("📌 " + " | ".join(filter_info))
        
        # 统计信息
        total_hours = sum(r[8] for r in records)
        total_cost = sum(r[9] for r in records)
        
        with col_stats:
            st.caption(f"📊 统计：共 {len(records)} 条记录 | 总机时 {total_hours:.1f}小时 | 总费用 {total_cost}元")
        
        # 显示记录列表 - 使用简洁两行布局
        st.markdown(f"### 📝 记录详情 (共 {len(records)} 条)")
        
        # 添加美化样式
        st.markdown("""
        <style>
        /* 美化分割线 */
        .compact-divider {
            margin: 6px 0 !important;
            border: none;
            border-top: 1px solid #e8e8e8;
        }
        /* 美化详情展开区域 */
        .detail-content {
            padding: 8px 0;
        }
        /* 美化备注区域 */
        .remark-box {
            margin-top: 8px;
            padding: 8px 12px;
            background-color: #f0f7ff;
            border-radius: 6px;
            border-left: 4px solid #1890ff;
            font-size: 0.9em;
            color: #333;
        }
        /* 图标颜色调整 */
        .icon-gray {
            opacity: 0.7;
        }
        </style>
        """, unsafe_allow_html=True)
        
        for i, record in enumerate(records, 1):
            record_id = record[0]
            
            # 提取记录数据
            name = record[4] or "未填写"
            equipment = record[7] or "未指定"
            contact = record[5] or "未填写"
            test_date = record[2]
            test_time = record[3] or "08:00-09:00"
            advisor = record[6] or "未填写"
            cost = record[9]
            hours = record[8]
            remark = record[10]
            
            # 第一行：姓名|设备|手机号 + 测试日期|时间段 + 编辑按钮
            col1_left, col1_middle, col1_right = st.columns([3, 2, 1])
            
            with col1_left:
                # 姓名 | 设备 | 手机号 - 使用Markdown格式而非HTML
                contact_icon = "📧" if "@" in contact else "📞"
                # 使用更简单的格式，或者使用st.markdown的html特性
                html_content = f"**{name}** | **{equipment}** | {contact_icon} {contact}"
                st.markdown(html_content)
            
            with col1_middle:
                # 测试日期 | 时间段 - 简化格式
                html_content = f"📅 {test_date} | 🕒 {test_time}"
                st.markdown(html_content)
            
            with col1_right:
                # 编辑按钮
                edit_key = f"edit_{record_id}_{i}"
                if st.button(f"✏️ 编辑", key=edit_key, use_container_width=True, 
                           help=f"编辑 {name} 的记录"):
                    load_record_for_editing(record_id)
            
            # 第二行：查看详情按钮
            detail_label = f"📋 查看详情"
            
            # 创建详情展开器
            with st.expander(detail_label):
                # 构建紧凑的信息字符串
                detail_info = []
                
                # 领导信息
                if advisor and advisor != "未填写":
                    detail_info.append(f"👨‍🏫 领导： {advisor}")
                
                # 机时信息
                detail_info.append(f"⏱️ 机时： {hours:.1f}小时")
                
                # 费用信息
                cost_info = f"{cost}元" if cost > 0 else "免费"
                detail_info.append(f"💵 费用： {cost_info}")
                
                # 登记时间
                register_date = record[1].split()[0] if record[1] else "未知"
                detail_info.append(f"📅 登记： {register_date}")
                
                # 将所有信息组合在一行，用分隔符分隔
                separator = "&nbsp;&nbsp;|&nbsp;&nbsp;"
                info_html = f"<div class='detail-content'>{separator.join(detail_info)}</div>"
                st.markdown(info_html, unsafe_allow_html=True)
                
                # 备注信息（如果有）
                if remark:
                    remark_html = f"<div class='remark-box'>📝 <strong>备注：</strong> {remark}</div>"
                    st.markdown(remark_html, unsafe_allow_html=True)
            
            # 添加美化分割线
            if i < len(records):
                st.markdown('<div class="compact-divider"></div>', unsafe_allow_html=True)
    
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
            equipment = st.text_input("实验设备 *", 
                                    value=st.session_state.form_data.get('equipment', ''),
                                    placeholder="请输入实验设备名称",
                                    help="请在设备管理中先添加设备")
        else:
            # 直接选择设备
            current_equipment = st.session_state.form_data.get('equipment', '')
            default_index = 0
            if current_equipment in preset_devices:
                default_index = preset_devices.index(current_equipment)
            
            equipment = st.selectbox(
                "实验设备 *",
                options=preset_devices,
                index=default_index,
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
                        success_container.success(f"✅ 记录{action}成功！")
                        
                        # 清空表单
                        clear_form()
                        
                        # 如果是编辑模式，自动返回查看记录页面
                        if st.session_state.current_edit_id:
                            st.session_state.current_edit_id = None
                            st.session_state.menu = "📋 查看记录"
                            time.sleep(1)
                            success_container.empty()
                            st.rerun()
                        else:
                            # 如果是新增记录，等待2秒后自动刷新表单（保持在同一页面）
                            time.sleep(2)
                            success_container.empty()
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
        else:
            if st.button("📋 查看记录", use_container_width=True):
                st.session_state.menu = "📋 查看记录"
                st.rerun()

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
    """显示设备管理页面 - 极简版本"""
    st.header("⚙️ 设备管理")
    
    # 先检查是否已认证
    if not st.session_state.is_authenticated:
        with st.container():
            st.warning("需要验证管理员密码才能管理设备")
            
            with st.form("equipment_auth_form"):
                password = st.text_input("请输入管理员密码", type="password", 
                                       key="equipment_pwd")
                submitted = st.form_submit_button("验证")
                
                if submitted:
                    if verify_password(password):
                        st.session_state.is_authenticated = True
                        st.success("验证成功！")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("密码错误！")
            
            if not st.session_state.is_authenticated:
                st.stop()
    
    try:
        from utils import Utils
        
        # 获取所有设备
        current_devices = Utils.get_preset_equipment()
        
        # 显示当前设备列表
        st.subheader("设备列表")
        
        if not current_devices:
            st.info("暂无设备")
        else:
            # 显示设备列表
            for i, device in enumerate(current_devices, 1):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{i}.** {device}")
                with col2:
                    # 删除按钮
                    delete_key = f"delete_device_{i}"
                    if st.button("删除", key=delete_key, use_container_width=True):
                        # 直接删除，不再需要确认对话框
                        if st.session_state.db_manager.delete_equipment_by_name(device):
                            st.success(f"已删除设备: {device}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"删除设备失败")
        
        st.markdown("---")
        
        # 添加新设备 - 极简版本
        st.subheader("添加新设备")
        
        # 使用简洁的表单
        with st.form("add_equipment_form", clear_on_submit=True):
            new_device = st.text_input("设备名称", placeholder="请输入设备名称")
            
            # 只有一个保存按钮
            submitted = st.form_submit_button("保存", type="primary", use_container_width=True)
            
            if submitted:
                if not new_device or not new_device.strip():
                    st.error("请输入设备名称")
                else:
                    device_name = new_device.strip()
                    
                    # 检查是否已存在
                    existing_devices = Utils.get_preset_equipment()
                    if device_name in existing_devices:
                        st.warning(f"设备 '{device_name}' 已存在")
                    else:
                        # 添加到数据库
                        if st.session_state.db_manager.add_equipment(device_name):
                            st.success(f"已添加设备: {device_name}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("添加设备失败")
        
        # 只保留恢复默认按钮
        st.markdown("---")
        if st.button("恢复默认设备", use_container_width=True):
            # 直接恢复默认，不再需要确认对话框
            default_devices = ["疲劳性能试验机", "透射电子显微镜"]
            restored_count = 0
            
            with st.spinner("正在恢复默认设备..."):
                for device in default_devices:
                    # 检查是否已存在
                    existing_devices = Utils.get_preset_equipment()
                    if device not in existing_devices:
                        if st.session_state.db_manager.add_equipment(device):
                            restored_count += 1
            
            if restored_count > 0:
                st.success(f"已恢复 {restored_count} 个默认设备")
                time.sleep(1)
                st.rerun()
            else:
                st.info("默认设备已全部存在")
        
    except Exception as e:
        logger.error(f"设备管理失败: {e}", exc_info=True)
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
