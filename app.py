import streamlit as st

# 仅非登录界面时设置宽屏
if 'logged_in' in st.session_state and st.session_state.get('logged_in', False):
    st.set_page_config(layout="wide")

import sqlite3
import pandas as pd
from datetime import date
from io import BytesIO

# 创建Excel模板下载函数
def create_excel_template(columns):
    df = pd.DataFrame(columns=columns)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Template')
    output.seek(0)
    return output

# 初始化数据库
conn = sqlite3.connect('expenses.db', check_same_thread=False)
c = conn.cursor()

# 创建费用记录表
c.execute('''
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expense_date DATE,
        department TEXT,
        company TEXT,
        budget_item TEXT,
        employee TEXT,
        amount REAL,
        description TEXT,
        status TEXT DEFAULT 'pending'
    )
''')

# 创建配置表
c.execute('''
    CREATE TABLE IF NOT EXISTS config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT NOT NULL,
        code TEXT NOT NULL,
        description TEXT NOT NULL,
        sap_code TEXT NOT NULL,
        sap_description TEXT NOT NULL,
        UNIQUE(key, code, description)
    )
''')

# 创建角色表
c.execute('''
    CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role_name TEXT NOT NULL,
        description TEXT,
        UNIQUE(role_name)
    )
''')

# 创建权限表
c.execute('''
    CREATE TABLE IF NOT EXISTS permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        module_name TEXT NOT NULL,
        permission_name TEXT NOT NULL,
        description TEXT,
        UNIQUE(module_name, permission_name)
    )
''')

# 创建角色权限关联表
c.execute('''
    CREATE TABLE IF NOT EXISTS role_permissions (
        role_id INTEGER,
        permission_id INTEGER,
        FOREIGN KEY (role_id) REFERENCES roles (id),
        FOREIGN KEY (permission_id) REFERENCES permissions (id),
        PRIMARY KEY (role_id, permission_id)
    )
''')

# 创建用户表
c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        user_name TEXT NOT NULL,
        password TEXT NOT NULL,
        role_id INTEGER,
        company_code TEXT,
        department_code TEXT,
        FOREIGN KEY (role_id) REFERENCES roles (id),
        UNIQUE(user_id)
    )
''')

# 创建记账记录表（如未存在）
c.execute('''
    CREATE TABLE IF NOT EXISTS expense_bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expense_id INTEGER,
        booking_date DATE,
        sap_account_code TEXT,
        sap_account_desc TEXT,
        sap_cost_center_code TEXT,
        sap_cost_center_desc TEXT,
        debit_amount REAL,
        credit_amount REAL,
        sap_employee_code TEXT,
        sap_employee_desc TEXT,
        FOREIGN KEY (expense_id) REFERENCES expenses (id)
    )
''')

# 创建entry表（如未存在）
c.execute('''
    CREATE TABLE IF NOT EXISTS entry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voucher_no INTEGER,
        expense_id INTEGER,
        entry_type TEXT,
        booking_date DATE,
        sap_account_code TEXT,
        sap_account_desc TEXT,
        sap_cost_center_code TEXT,
        sap_cost_center_desc TEXT,
        debit_amount REAL,
        credit_amount REAL,
        sap_employee_code TEXT,
        sap_employee_desc TEXT,
        voucher_date DATE,
        post_date DATE
    )
''')

# 确保expenses表有status字段（兼容老库自动升级）
try:
    c.execute("SELECT status FROM expenses LIMIT 1")
except Exception:
    c.execute("ALTER TABLE expenses ADD COLUMN status TEXT DEFAULT 'pending'")
    conn.commit()

# 确保users表有company_code和department_code字段（兼容老库自动升级）
try:
    c.execute("SELECT company_code FROM users LIMIT 1")
except Exception:
    c.execute("ALTER TABLE users ADD COLUMN company_code TEXT")
    conn.commit()
try:
    c.execute("SELECT department_code FROM users LIMIT 1")
except Exception:
    c.execute("ALTER TABLE users ADD COLUMN department_code TEXT")
    conn.commit()

# 初始化默认权限
default_permissions = [
    ('expense', 'create', '创建报销记录'),
    ('expense', 'view', '查看报销记录'),
    ('expense', 'export', '导出报销记录'),
    ('expense', 'book', '报销记账'),
    ('master_data', 'manage', '管理主数据'),
    ('user', 'manage', '管理用户'),
    ('role', 'manage', '管理角色')
]

for module, perm, desc in default_permissions:
    c.execute("INSERT OR IGNORE INTO permissions (module_name, permission_name, description) VALUES (?, ?, ?)",
             (module, perm, desc))

# 确保至少有一个管理员角色
admin_role = c.execute("SELECT id FROM roles WHERE role_name='admin'").fetchone()
if not admin_role:
    c.execute("INSERT INTO roles (role_name, description) VALUES (?, ?)", 
             ("admin", "系统管理员"))
    admin_role_id = c.execute("SELECT id FROM roles WHERE role_name='admin'").fetchone()[0]
    # 为管理员角色分配所有权限
    for perm_id in c.execute("SELECT id FROM permissions").fetchall():
        c.execute("INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
                 (admin_role_id, perm_id[0]))

# 确保至少有一个管理员用户
admin_user = c.execute("SELECT id FROM users WHERE user_id='admin'").fetchone()
if not admin_user:
    admin_role_id = c.execute("SELECT id FROM roles WHERE role_name='admin'").fetchone()[0]
    c.execute("INSERT INTO users (user_id, user_name, password, role_id) VALUES (?, ?, ?, ?)", 
             ("admin", "管理员", "admin123", admin_role_id))

conn.commit()

# 初始化 session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if 'user_id' not in st.session_state:
    st.session_state.user_id = ""
    
if 'user_role' not in st.session_state:
    st.session_state.user_role = ""
    
if 'current_page' not in st.session_state:
    st.session_state.current_page = "报销采集"

# 登录界面
if not st.session_state.logged_in:
    st.title("🔐 登录系统")
    
    with st.form("login_form"):
        user_id = st.text_input("用户ID")
        password = st.text_input("密码", type="password")
        submitted = st.form_submit_button("登录")
        
        if submitted:
            user = c.execute("SELECT user_id, user_name, role_id FROM users WHERE user_id=? AND password=?", 
                           (user_id, password)).fetchone()
            if user:
                st.session_state.logged_in = True
                st.session_state.user_id = user[0]
                st.session_state.user_role = c.execute("SELECT role_name FROM roles WHERE id=?", (user[2],)).fetchone()[0]
                st.success(f"欢迎回来，{user[1]}！")
                st.experimental_rerun()
            else:
                st.error("用户ID或密码错误！")
    
    st.info("默认管理员账号: admin / 密码: admin123")
    st.stop()

# 页面选择
st.sidebar.title("导航")
st.sidebar.write(f"当前用户: {st.session_state.user_id}")

# 登出按钮
if st.sidebar.button("登出"):
    st.session_state.logged_in = False
    st.session_state.user_id = ""
    st.session_state.user_role = ""
    st.experimental_rerun()

# 创建导航按钮（每行2个，等高等宽，均匀分布）
nav_labels = ["📝 报销采集", "🔍 报销查看", "📊 主数据管理", "👥 用户角色管理", "📖 报销记账", "📑 记账查看"]
nav_pages = ["报销采集", "报销查看", "主数据管理", "用户角色管理", "报销记账", "记账查看"]
nav_pairs = [nav_labels[i:i+2] for i in range(0, len(nav_labels), 2)]
nav_page_pairs = [nav_pages[i:i+2] for i in range(0, len(nav_pages), 2)]
for pair_labels, pair_pages in zip(nav_pairs, nav_page_pairs):
    cols = st.sidebar.columns(2)
    for i, (label, page) in enumerate(zip(pair_labels, pair_pages)):
        if cols[i].button(label, use_container_width=True):
            st.session_state.current_page = page
st.sidebar.markdown('---')

# 根据 session state 显示对应页面
if st.session_state.current_page == "报销采集":
    st.title("➕ 报销采集")
    with st.form("expense_form"):
        expense_date = st.date_input("日期", value=date.today())
        department = st.selectbox("部门", 
            [row[1] for row in c.execute("SELECT code, description FROM config WHERE key='department'")])
        company = st.selectbox("公司", 
            [row[1] for row in c.execute("SELECT code, description FROM config WHERE key='company'")])
        budget_item = st.selectbox("预算科目", 
            [row[1] for row in c.execute("SELECT code, description FROM config WHERE key='budget_item'")])
        # 报销人逻辑
        if st.session_state.user_role == 'admin':
            employee = st.selectbox("报销人", 
                [row[1] for row in c.execute("SELECT code, description FROM config WHERE key='employee'")])
        else:
            # 普通用户只能选自己
            user_info = c.execute("SELECT user_name FROM users WHERE user_id=?", (st.session_state.user_id,)).fetchone()
            employee = user_info[0] if user_info else ""
            st.text_input("报销人", value=employee, disabled=True)
        amount = st.number_input("金额", min_value=0.00, step=0.00)
        description = st.text_input("摘要 / 说明")
        submitted = st.form_submit_button("提交")
        if submitted:
            dept_code = c.execute("SELECT code FROM config WHERE key='department' AND description=?", (department,)).fetchone()[0]
            comp_code = c.execute("SELECT code FROM config WHERE key='company' AND description=?", (company,)).fetchone()[0]
            budget_code = c.execute("SELECT code FROM config WHERE key='budget_item' AND description=?", (budget_item,)).fetchone()[0]
            if st.session_state.user_role == 'admin':
                emp_code = c.execute("SELECT code FROM config WHERE key='employee' AND description=?", (employee,)).fetchone()[0]
            else:
                # 普通用户自动用自己
                emp_code = c.execute("SELECT code FROM config WHERE key='employee' AND description=?", (employee,)).fetchone()[0]
            c.execute('''
                INSERT INTO expenses (expense_date, department, company, budget_item, employee, amount, description, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            ''', (expense_date, dept_code, comp_code, budget_code, emp_code, amount, description))
            conn.commit()
            st.success("✅ 记录已保存！")

elif st.session_state.current_page == "报销查看":
    st.title("📊 报销记录查看")
    # 筛选条件
    col1, col2 = st.columns(2)
    with col1:
        filter_department = st.selectbox("筛选部门", [""] + 
            [row[1] for row in c.execute("SELECT code, description FROM config WHERE key='department'")])
        filter_employee = st.selectbox("筛选报销人", [""] + 
            [row[1] for row in c.execute("SELECT code, description FROM config WHERE key='employee'")])
    with col2:
        filter_company = st.selectbox("筛选公司", [""] + 
            [row[1] for row in c.execute("SELECT code, description FROM config WHERE key='company'")])
        filter_budget = st.selectbox("筛选预算科目", [""] + 
            [row[1] for row in c.execute("SELECT code, description FROM config WHERE key='budget_item'")])
    amount_col1, amount_col2 = st.columns(2)
    with amount_col1:
        min_amount = st.number_input("金额范围（从）", value=0.0, step=100.0)
    with amount_col2:
        max_amount = st.number_input("金额范围（至）", value=0.0, step=100.0)
    if max_amount > 0 and max_amount < min_amount:
        st.warning("最大金额不能小于最小金额")
        max_amount = min_amount
    search_clicked = st.button("🔍 执行搜索")
    if search_clicked:
        query = "SELECT e.expense_date as '日期', \
                d.description as '部门', \
                c.description as '公司', \
                b.description as '预算科目', \
                em.description as '报销人', \
                e.amount as '金额', \
                e.description as '摘要' \
                FROM expenses e \
                LEFT JOIN config d ON e.department = d.code AND d.key = 'department' \
                LEFT JOIN config c ON e.company = c.code AND c.key = 'company' \
                LEFT JOIN config b ON e.budget_item = b.code AND b.key = 'budget_item' \
                LEFT JOIN config em ON e.employee = em.code AND em.key = 'employee'"
        where_clauses = []
        if st.session_state.user_role != 'admin':
            # 普通用户只能看自己
            user_info = c.execute("SELECT user_name FROM users WHERE user_id=?", (st.session_state.user_id,)).fetchone()
            if user_info:
                emp_code = c.execute("SELECT code FROM config WHERE key='employee' AND description=?", (user_info[0],)).fetchone()[0]
                where_clauses.append(f"e.employee='{emp_code}'")
        if filter_department:
            dept_code = c.execute("SELECT code FROM config WHERE key='department' AND description=?", 
                                (filter_department,)).fetchone()[0]
            where_clauses.append(f"e.department='{dept_code}'")
        if filter_company:
            comp_code = c.execute("SELECT code FROM config WHERE key='company' AND description=?", 
                                (filter_company,)).fetchone()[0]
            where_clauses.append(f"e.company='{comp_code}'")
        if filter_employee:
            emp_code = c.execute("SELECT code FROM config WHERE key='employee' AND description=?", 
                                (filter_employee,)).fetchone()[0]
            where_clauses.append(f"e.employee='{emp_code}'")
        if filter_budget:
            budget_code = c.execute("SELECT code FROM config WHERE key='budget_item' AND description=?", 
                                (filter_budget,)).fetchone()[0]
            where_clauses.append(f"e.budget_item='{budget_code}'")
        if min_amount > 0:
            where_clauses.append(f"e.amount >= {min_amount}")
        if max_amount > 0:
            where_clauses.append(f"e.amount <= {max_amount}")
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        query += " ORDER BY expense_date DESC"
        df = pd.read_sql_query(query, conn)
        st.dataframe(df)
        # 导出功能
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Expenses')
        output.seek(0)
        st.download_button(
            label="📥 导出为 Excel",
            data=output,
            file_name='expenses.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

elif st.session_state.current_page == "主数据管理":
    st.title("📊 主数据管理")
    config_tabs = st.tabs(["部门", "公司", "预算科目", "报销人"])
    
    with config_tabs[0]:
        st.subheader("部门管理")
        # 手动添加部分
        col1, col2 = st.columns(2)
        with col1:
            code = st.text_input("部门编码")
            sap_code = st.text_input("SAP成本中心", value=code)
        with col2:
            desc = st.text_input("部门描述")
            sap_desc = st.text_input("SAP成本中心描述", value=desc)
        if st.button("添加部门") and code and desc:
            try:
                c.execute("INSERT OR IGNORE INTO config (key, code, description, sap_code, sap_description) VALUES (?, ?, ?, ?, ?)", 
                        ("department", code, desc, sap_code, sap_desc))
                conn.commit()
                st.success(f"部门 '{desc}({code})' 已添加！")
            except sqlite3.IntegrityError:
                st.warning(f"部门编码 {code} 或描述 {desc} 已存在！")
        
        # Excel导入部分
        st.divider()
        st.subheader("批量导入")
        col1, col2 = st.columns([3, 1])
        with col1:
            uploaded_file = st.file_uploader("上传Excel文件", type=["xlsx"], key="department_uploader")
        with col2:
            dept_template = create_excel_template(["部门编码", "部门描述", "SAP成本中心", "SAP成本中心描述"])
            st.download_button(
                label="📥 下载模板",
                data=dept_template,
                file_name="部门导入模板.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file)
                if all(col in df.columns for col in ["部门编码", "部门描述", "SAP成本中心", "SAP成本中心描述"]):
                    for _, row in df.iterrows():
                        try:
                            c.execute("INSERT OR IGNORE INTO config (key, code, description, sap_code, sap_description) VALUES (?, ?, ?, ?, ?)",
                                    ("department", row["部门编码"], row["部门描述"], row["SAP成本中心"], row["SAP成本中心描述"]))
                        except sqlite3.IntegrityError:
                            continue
                    conn.commit()
                    st.success("Excel数据导入成功！")
                else:
                    st.error("Excel文件格式不正确！请确保包含：部门编码、部门描述、SAP成本中心、SAP成本中心描述")
            except Exception as e:
                st.error(f"导入失败：{str(e)}")
        
        # 显示部门列表
        st.divider()
        st.subheader("部门列表")
        dept_df = pd.read_sql_query("SELECT code AS 编码, description AS 描述, sap_code AS 'SAP成本中心', sap_description AS 'SAP成本中心描述' FROM config WHERE key='department' ORDER BY code", conn)
        st.dataframe(dept_df)

    with config_tabs[1]:
        st.subheader("公司管理")
        # 手动添加部分
        col1, col2 = st.columns(2)
        with col1:
            code = st.text_input("公司编码")
            sap_code = st.text_input("SAP公司代码", value=code)
        with col2:
            desc = st.text_input("公司描述")
            sap_desc = st.text_input("SAP公司描述", value=desc)
        if st.button("添加公司") and code and desc:
            try:
                c.execute("INSERT OR IGNORE INTO config (key, code, description, sap_code, sap_description) VALUES (?, ?, ?, ?, ?)", 
                        ("company", code, desc, sap_code, sap_desc))
                conn.commit()
                st.success(f"公司 '{desc}({code})' 已添加！")
            except sqlite3.IntegrityError:
                st.warning(f"公司编码 {code} 或描述 {desc} 已存在！")
        
        # Excel导入部分
        st.divider()
        st.subheader("批量导入")
        col1, col2 = st.columns([3, 1])
        with col1:
            uploaded_file = st.file_uploader("上传Excel文件", type=["xlsx"], key="company_uploader")
        with col2:
            comp_template = create_excel_template(["公司编码", "公司描述", "SAP公司代码", "SAP公司描述"])
            st.download_button(
                label="📥 下载模板",
                data=comp_template,
                file_name="公司导入模板.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file)
                if all(col in df.columns for col in ["公司编码", "公司描述", "SAP公司代码", "SAP公司描述"]):
                    for _, row in df.iterrows():
                        try:
                            c.execute("INSERT OR IGNORE INTO config (key, code, description, sap_code, sap_description) VALUES (?, ?, ?, ?, ?)",
                                    ("company", row["公司编码"], row["公司描述"], row["SAP公司代码"], row["SAP公司描述"]))
                        except sqlite3.IntegrityError:
                            continue
                    conn.commit()
                    st.success("Excel数据导入成功！")
                else:
                    st.error("Excel文件格式不正确！请确保包含：公司编码、公司描述、SAP公司代码、SAP公司描述")
            except Exception as e:
                st.error(f"导入失败：{str(e)}")
        
        # 显示公司列表
        st.divider()
        st.subheader("公司列表")
        comp_df = pd.read_sql_query("SELECT code AS 编码, description AS 描述, sap_code AS 'SAP公司代码', sap_description AS 'SAP公司描述' FROM config WHERE key='company' ORDER BY code", conn)
        st.dataframe(comp_df)

    with config_tabs[2]:
        st.subheader("预算科目管理")
        # 手动添加部分
        col1, col2 = st.columns(2)
        with col1:
            code = st.text_input("预算科目编码")
            sap_code = st.text_input("SAP核算科目", value=code)
        with col2:
            desc = st.text_input("预算科目描述")
            sap_desc = st.text_input("SAP核算科目描述", value=desc)
        if st.button("添加预算科目") and code and desc:
            try:
                c.execute("INSERT OR IGNORE INTO config (key, code, description, sap_code, sap_description) VALUES (?, ?, ?, ?, ?)", 
                        ("budget_item", code, desc, sap_code, sap_desc))
                conn.commit()
                st.success(f"预算科目 '{desc}({code})' 已添加！")
            except sqlite3.IntegrityError:
                st.warning(f"预算科目编码 {code} 或描述 {desc} 已存在！")
        
        # Excel导入部分
        st.divider()
        st.subheader("批量导入")
        col1, col2 = st.columns([3, 1])
        with col1:
            uploaded_file = st.file_uploader("上传Excel文件", type=["xlsx"], key="budget_uploader")
        with col2:
            budget_template = create_excel_template(["预算科目编码", "预算科目描述", "SAP核算科目", "SAP核算科目描述"])
            st.download_button(
                label="📥 下载模板",
                data=budget_template,
                file_name="预算科目导入模板.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file)
                if all(col in df.columns for col in ["预算科目编码", "预算科目描述", "SAP核算科目", "SAP核算科目描述"]):
                    for _, row in df.iterrows():
                        try:
                            c.execute("INSERT OR IGNORE INTO config (key, code, description, sap_code, sap_description) VALUES (?, ?, ?, ?, ?)",
                                    ("budget_item", row["预算科目编码"], row["预算科目描述"], row["SAP核算科目"], row["SAP核算科目描述"]))
                        except sqlite3.IntegrityError:
                            continue
                    conn.commit()
                    st.success("Excel数据导入成功！")
                else:
                    st.error("Excel文件格式不正确！请确保包含：预算科目编码、预算科目描述、SAP核算科目、SAP核算科目描述")
            except Exception as e:
                st.error(f"导入失败：{str(e)}")
        
        # 显示预算科目列表
        st.divider()
        st.subheader("预算科目列表")
        budget_df = pd.read_sql_query("SELECT code AS 编码, description AS 描述, sap_code AS 'SAP核算科目', sap_description AS 'SAP核算科目描述' FROM config WHERE key='budget_item' ORDER BY code", conn)
        st.dataframe(budget_df)

    with config_tabs[3]:
        st.subheader("报销人管理")
        # 手动添加部分
        col1, col2 = st.columns(2)
        with col1:
            code = st.text_input("报销人编码")
            sap_code = st.text_input("SAP员工代码", value=code)
        with col2:
            desc = st.text_input("报销人姓名")
            sap_desc = st.text_input("SAP员工姓名", value=desc)
        if st.button("添加报销人") and code and desc:
            try:
                c.execute("INSERT OR IGNORE INTO config (key, code, description, sap_code, sap_description) VALUES (?, ?, ?, ?, ?)", 
                        ("employee", code, desc, sap_code, sap_desc))
                conn.commit()
                st.success(f"报销人 '{desc}({code})' 已添加！")
            except sqlite3.IntegrityError:
                st.warning(f"报销人编码 {code} 或描述 {desc} 已存在！")
        
        # Excel导入部分
        st.divider()
        st.subheader("批量导入")
        col1, col2 = st.columns([3, 1])
        with col1:
            uploaded_file = st.file_uploader("上传Excel文件", type=["xlsx"], key="employee_uploader")
        with col2:
            emp_template = create_excel_template(["报销人编码", "报销人姓名", "SAP员工代码", "SAP员工姓名"])
            st.download_button(
                label="📥 下载模板",
                data=emp_template,
                file_name="报销人导入模板.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file)
                if all(col in df.columns for col in ["报销人编码", "报销人姓名", "SAP员工代码", "SAP员工姓名"]):
                    for _, row in df.iterrows():
                        try:
                            c.execute("INSERT OR IGNORE INTO config (key, code, description, sap_code, sap_description) VALUES (?, ?, ?, ?, ?)",
                                    ("employee", row["报销人编码"], row["报销人姓名"], row["SAP员工代码"], row["SAP员工姓名"]))
                        except sqlite3.IntegrityError:
                            continue
                    conn.commit()
                    st.success("Excel数据导入成功！")
                else:
                    st.error("Excel文件格式不正确！请确保包含：报销人编码、报销人姓名、SAP员工代码、SAP员工姓名")
            except Exception as e:
                st.error(f"导入失败：{str(e)}")
        
        # 显示报销人列表
        st.divider()
        st.subheader("报销人列表")
        emp_df = pd.read_sql_query("SELECT code AS 编码, description AS 姓名, sap_code AS 'SAP员工代码', sap_description AS 'SAP员工姓名' FROM config WHERE key='employee' ORDER BY code", conn)
        st.dataframe(emp_df)

elif st.session_state.current_page == "用户角色管理":
    st.title("👥 用户及角色管理")
    user_role_tabs = st.tabs(["角色管理", "用户管理"])
    
    with user_role_tabs[0]:
        st.subheader("角色管理")
        
        # 创建新角色
        with st.expander("创建新角色", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                new_role_name = st.text_input("角色名称")
                new_role_desc = st.text_area("角色描述")
            
            # 权限选择
            st.subheader("权限设置")
            permissions = c.execute("SELECT id, module_name, permission_name, description FROM permissions ORDER BY module_name, permission_name").fetchall()
            
            # 按模块分组显示权限
            modules = {}
            for perm in permissions:
                if perm[1] not in modules:
                    modules[perm[1]] = []
                modules[perm[1]].append(perm)
            
            for module_name, perms in modules.items():
                st.write(f"**{module_name}**")
                cols = st.columns(3)
                for i, perm in enumerate(perms):
                    with cols[i % 3]:
                        st.checkbox(f"{perm[3]}", key=f"perm_{perm[0]}")
            
            if st.button("创建角色"):
                if new_role_name:
                    try:
                        c.execute("INSERT INTO roles (role_name, description) VALUES (?, ?)",
                                (new_role_name, new_role_desc))
                        role_id = c.execute("SELECT id FROM roles WHERE role_name=?", (new_role_name,)).fetchone()[0]
                        
                        # 添加选中的权限
                        for perm in permissions:
                            if st.session_state.get(f"perm_{perm[0]}"):
                                c.execute("INSERT INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
                                        (role_id, perm[0]))
                        
                        conn.commit()
                        st.success(f"角色 '{new_role_name}' 创建成功！")
                        st.experimental_rerun()
                    except sqlite3.IntegrityError:
                        st.error("角色名称已存在！")
                else:
                    st.warning("请输入角色名称！")
        
        # 显示现有角色
        st.divider()
        st.subheader("现有角色")
        roles_df = pd.read_sql_query("""
            SELECT r.role_name AS 角色名称, 
                   r.description AS 角色描述,
                   GROUP_CONCAT(p.description) AS 权限列表
            FROM roles r
            LEFT JOIN role_permissions rp ON r.id = rp.role_id
            LEFT JOIN permissions p ON rp.permission_id = p.id
            GROUP BY r.id
            ORDER BY r.role_name
        """, conn)
        st.dataframe(roles_df)
        
        # 编辑角色
        st.divider()
        st.subheader("编辑角色")
        role_to_edit = st.selectbox("选择要编辑的角色", 
            [row[0] for row in c.execute("SELECT role_name FROM roles WHERE role_name != 'admin'")])
        
        if role_to_edit:
            role_data = c.execute("SELECT id, description FROM roles WHERE role_name=?", (role_to_edit,)).fetchone()
            role_perms = c.execute("""
                SELECT permission_id FROM role_permissions 
                WHERE role_id=?
            """, (role_data[0],)).fetchall()
            role_perms = [p[0] for p in role_perms]
            
            new_desc = st.text_area("修改角色描述", value=role_data[1])
            
            st.write("修改权限设置")
            for module_name, perms in modules.items():
                st.write(f"**{module_name}**")
                cols = st.columns(3)
                for i, perm in enumerate(perms):
                    with cols[i % 3]:
                        st.checkbox(f"{perm[3]}", 
                                  value=perm[0] in role_perms,
                                  key=f"edit_perm_{perm[0]}")
            
            if st.button("保存修改"):
                c.execute("UPDATE roles SET description=? WHERE id=?", (new_desc, role_data[0]))
                
                # 更新权限
                c.execute("DELETE FROM role_permissions WHERE role_id=?", (role_data[0],))
                for perm in permissions:
                    if st.session_state.get(f"edit_perm_{perm[0]}"):
                        c.execute("INSERT INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
                                (role_data[0], perm[0]))
                
                conn.commit()
                st.success("角色更新成功！")
                st.experimental_rerun()
    
    with user_role_tabs[1]:
        st.subheader("用户管理")
        
        # 创建新用户
        with st.expander("创建新用户", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                new_user_id = st.text_input("用户ID")
                new_user_name = st.text_input("用户姓名")
                # 所属公司
                company_options = [row for row in c.execute("SELECT code, description FROM config WHERE key='company'")]
                new_user_company = st.selectbox("所属公司", options=[f"{code} | {desc}" for code, desc in company_options], index=0 if company_options else None)
                # 所属部门
                dept_options = [row for row in c.execute("SELECT code, description FROM config WHERE key='department'")]
                new_user_dept = st.selectbox("所属部门", options=[f"{code} | {desc}" for code, desc in dept_options], index=0 if dept_options else None)
            with col2:
                new_user_password = st.text_input("密码", type="password")
                new_user_role = st.selectbox("分配角色", 
                    [row[0] for row in c.execute("SELECT role_name FROM roles ORDER BY role_name")])
            if st.button("创建用户"):
                if new_user_id and new_user_name and new_user_password:
                    try:
                        role_id = c.execute("SELECT id FROM roles WHERE role_name=?", (new_user_role,)).fetchone()[0]
                        company_code = new_user_company.split(" | ")[0] if new_user_company else None
                        dept_code = new_user_dept.split(" | ")[0] if new_user_dept else None
                        c.execute("INSERT INTO users (user_id, user_name, password, role_id, company_code, department_code) VALUES (?, ?, ?, ?, ?, ?)",
                                (new_user_id, new_user_name, new_user_password, role_id, company_code, dept_code))
                        conn.commit()
                        st.success(f"用户 '{new_user_name}' 创建成功！")
                        st.experimental_rerun()
                    except sqlite3.IntegrityError:
                        st.error("用户ID已存在！")
                else:
                    st.warning("请填写所有必填字段！")
        
        # 显示用户列表
        st.divider()
        st.subheader("用户列表")
        users_df = pd.read_sql_query("""
            SELECT u.user_id AS 用户ID, 
                   u.user_name AS 用户姓名,
                   r.role_name AS 角色
            FROM users u
            JOIN roles r ON u.role_id = r.id
            ORDER BY u.user_id
        """, conn)
        st.dataframe(users_df)
        
        # 编辑用户
        st.divider()
        st.subheader("编辑用户")
        user_to_edit = st.selectbox("选择要编辑的用户", 
            [row[0] for row in c.execute("SELECT user_id FROM users WHERE user_id != 'admin'")])
        if user_to_edit:
            user_data = c.execute("""
                SELECT u.id, u.user_name, u.role_id, r.role_name, u.company_code, u.department_code
                FROM users u
                JOIN roles r ON u.role_id = r.id
                WHERE u.user_id=?
            """, (user_to_edit,)).fetchone()
            new_name = st.text_input("修改用户姓名", value=user_data[1])
            new_password = st.text_input("修改密码", type="password")
            new_role = st.selectbox("修改角色", 
                [row[0] for row in c.execute("SELECT role_name FROM roles ORDER BY role_name")],
                index=[row[0] for row in c.execute("SELECT role_name FROM roles ORDER BY role_name")].index(user_data[3]))
            # 所属公司
            company_options = [row for row in c.execute("SELECT code, description FROM config WHERE key='company'")]
            company_display = [f"{code} | {desc}" for code, desc in company_options]
            company_index = 0
            for idx, (code, _) in enumerate(company_options):
                if code == user_data[4]:
                    company_index = idx
                    break
            new_company = st.selectbox("所属公司", options=company_display, index=company_index if company_options else 0)
            # 所属部门
            dept_options = [row for row in c.execute("SELECT code, description FROM config WHERE key='department'")]
            dept_display = [f"{code} | {desc}" for code, desc in dept_options]
            dept_index = 0
            for idx, (code, _) in enumerate(dept_options):
                if code == user_data[5]:
                    dept_index = idx
                    break
            new_dept = st.selectbox("所属部门", options=dept_display, index=dept_index if dept_options else 0)
            if st.button("保存用户修改"):
                try:
                    role_id = c.execute("SELECT id FROM roles WHERE role_name=?", (new_role,)).fetchone()[0]
                    company_code = new_company.split(" | ")[0] if new_company else None
                    dept_code = new_dept.split(" | ")[0] if new_dept else None
                    if new_password:
                        c.execute("""
                            UPDATE users 
                            SET user_name=?, password=?, role_id=?, company_code=?, department_code=?
                            WHERE id=?
                        """, (new_name, new_password, role_id, company_code, dept_code, user_data[0]))
                    else:
                        c.execute("""
                            UPDATE users 
                            SET user_name=?, role_id=?, company_code=?, department_code=?
                            WHERE id=?
                        """, (new_name, role_id, company_code, dept_code, user_data[0]))
                    conn.commit()
                    st.success("用户信息更新成功！")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"更新失败：{str(e)}")

elif st.session_state.current_page == "报销记账":
    st.title("📖 报销记账")
    
    # 获取未记账的报销记录
    unbooked_expenses = pd.read_sql_query("""
        SELECT e.id, e.expense_date, e.amount, e.description,
               d.description as department,
               c.description as company,
               b.description as budget_item,
               em.description as employee,
               b.sap_code as sap_account_code,
               b.sap_description as sap_account_desc,
               d.sap_code as sap_cost_center_code,
               d.sap_description as sap_cost_center_desc,
               em.sap_code as sap_employee_code,
               em.sap_description as sap_employee_desc
        FROM expenses e
        LEFT JOIN config d ON e.department = d.code AND d.key = 'department'
        LEFT JOIN config c ON e.company = c.code AND c.key = 'company'
        LEFT JOIN config b ON e.budget_item = b.code AND b.key = 'budget_item'
        LEFT JOIN config em ON e.employee = em.code AND em.key = 'employee'
        WHERE e.status='pending'
        ORDER BY e.expense_date DESC
    """, conn)
    
    if unbooked_expenses.empty:
        st.info("没有待记账的报销记录")
    else:
        st.subheader("待记账报销记录（可多选）")
        # 自定义表格+checkbox
        selected_ids = []
        columns_to_show = ["expense_date", "department", "company", "budget_item", "employee", "amount", "description"]
        header_cols = st.columns([0.5] + [1]*len(columns_to_show))
        with header_cols[0]:
            st.markdown("**选择**")
        for i, col in enumerate(columns_to_show):
            with header_cols[i+1]:
                st.markdown(f"**{col}**")
        for idx, row in unbooked_expenses.iterrows():
            row_cols = st.columns([0.5] + [1]*len(columns_to_show))
            with row_cols[0]:
                checked = st.checkbox("", key=f"select_exp_{row['id']}")
                if checked:
                    selected_ids.append(row['id'])
            for i, col in enumerate(columns_to_show):
                with row_cols[i+1]:
                    st.write(row[col])
        selected_rows = unbooked_expenses[unbooked_expenses['id'].isin(selected_ids)]
        if not selected_rows.empty:
            # 记账成功弹窗（form外部，且只显示弹窗不显示表单）
            if st.session_state.get('voucher_modal', False):
                st.success(f"记账成功，凭证号{st.session_state.voucher_no}已经生成")
                if st.button("确认"):
                    st.session_state.voucher_modal = False
                    st.session_state.booking_rows = []
                    st.session_state.last_selected_ids = []
                    st.experimental_rerun()
            else:
                # 初始化借方行（每条报销一行）
                if 'booking_rows' not in st.session_state or st.session_state.get('last_selected_ids', []) != list(selected_rows['id']):
                    st.session_state.booking_rows = []
                    for _, row in selected_rows.iterrows():
                        st.session_state.booking_rows.append({
                            'type': 'debit',
                            'sap_account_code': row['sap_account_code'],
                            'sap_account_desc': row['sap_account_desc'],
                            'sap_cost_center_code': row['sap_cost_center_code'],
                            'sap_cost_center_desc': row['sap_cost_center_desc'],
                            'debit_amount': float(row['amount']),
                            'credit_amount': 0.0,
                            'sap_employee_code': row['sap_employee_code'],
                            'sap_employee_desc': row['sap_employee_desc'],
                            'voucher_date': date.today(),
                            'post_date': date.today(),
                            'expense_id': row['id']
                        })
                    st.session_state.last_selected_ids = list(selected_rows['id'])
                rows = st.session_state.booking_rows
                with st.form("booking_form", clear_on_submit=False):
                    st.subheader("记账信息")
                    for i, row in enumerate(rows):
                        with st.container():
                            st.markdown(f"#### 行项目 {i+1}")
                            col1, col2, col3 = st.columns([1,1,1])
                            with col1:
                                row_type = st.selectbox("借贷方", ["借方", "贷方"], index=0 if row['type']=="debit" else 1, key=f"row_type_{i}")
                            with col2:
                                voucher_date = st.date_input("凭证日期", value=row.get('voucher_date', date.today()), key=f"voucher_date_{i}")
                            with col3:
                                post_date = st.date_input("过账日期", value=row.get('post_date', date.today()), key=f"post_date_{i}")
                            col4, col5 = st.columns([2,2])
                            with col4:
                                sap_account_code = st.text_input("SAP科目", value=row['sap_account_code'], key=f"sap_account_code_{i}")
                                sap_account_desc = st.text_input("SAP核算科目描述", value=row['sap_account_desc'], key=f"sap_account_desc_{i}")
                            with col5:
                                sap_cost_center_code = st.text_input("成本中心", value=row['sap_cost_center_code'], key=f"sap_cost_center_code_{i}")
                                sap_cost_center_desc = st.text_input("成本中心描述", value=row['sap_cost_center_desc'], key=f"sap_cost_center_desc_{i}")
                            col6, col7, col8 = st.columns([1,1,2])
                            with col6:
                                if row_type == "借方":
                                    debit_amount = st.number_input("借方金额", value=row['debit_amount'], min_value=0.0, key=f"debit_amount_{i}", disabled=False)
                                    credit_amount = 0.0
                                else:
                                    debit_amount = 0.0
                                    credit_amount = st.number_input("贷方金额", value=row['credit_amount'], min_value=0.0, key=f"credit_amount_{i}", disabled=False)
                            with col7:
                                sap_employee_code = st.text_input("SAP员工代码", value=row['sap_employee_code'], key=f"sap_employee_code_{i}")
                            with col8:
                                sap_employee_desc = st.text_input("SAP员工姓名", value=row['sap_employee_desc'], key=f"sap_employee_desc_{i}")
                    remove_idx = None
                    if len(rows) > len(selected_rows):
                        remove_options = [f"第{i+1}行" for i in range(len(selected_rows), len(rows))]
                        remove_choice = st.selectbox("选择要删除的贷方行", remove_options, key="remove_row_select")
                        remove_btn = st.form_submit_button("删除选中行")
                        if remove_btn:
                            remove_idx = int(remove_choice.replace("第", "").replace("行", "")) - 1
                    for i, row in enumerate(rows):
                        row_type = st.session_state.get(f"row_type_{i}", "借方")
                        rows[i]['type'] = 'debit' if row_type == "借方" else 'credit'
                        rows[i]['voucher_date'] = st.session_state.get(f"voucher_date_{i}", date.today())
                        rows[i]['post_date'] = st.session_state.get(f"post_date_{i}", date.today())
                        rows[i]['sap_account_code'] = st.session_state.get(f"sap_account_code_{i}", "")
                        rows[i]['sap_account_desc'] = st.session_state.get(f"sap_account_desc_{i}", "")
                        rows[i]['sap_cost_center_code'] = st.session_state.get(f"sap_cost_center_code_{i}", "")
                        rows[i]['sap_cost_center_desc'] = st.session_state.get(f"sap_cost_center_desc_{i}", "")
                        rows[i]['debit_amount'] = st.session_state.get(f"debit_amount_{i}", 0.0)
                        rows[i]['credit_amount'] = st.session_state.get(f"credit_amount_{i}", 0.0)
                        rows[i]['sap_employee_code'] = st.session_state.get(f"sap_employee_code_{i}", "")
                        rows[i]['sap_employee_desc'] = st.session_state.get(f"sap_employee_desc_{i}", "")
                    if remove_idx is not None:
                        del rows[remove_idx]
                        st.session_state.booking_rows = rows
                        st.experimental_rerun()
                    total_debit = sum(r['debit_amount'] for r in rows)
                    total_credit = sum(r['credit_amount'] for r in rows)
                    st.markdown(f"**借方合计：{total_debit:.2f}    贷方合计：{total_credit:.2f}**")
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        add_row = st.form_submit_button("添加贷方行")
                    with col_btn2:
                        save = st.form_submit_button("保存")
                    if add_row:
                        rows.append({
                            'type': 'credit',
                            'sap_account_code': '',
                            'sap_account_desc': '',
                            'sap_cost_center_code': '',
                            'sap_cost_center_desc': '',
                            'debit_amount': 0.0,
                            'credit_amount': 0.0,
                            'sap_employee_code': '',
                            'sap_employee_desc': '',
                            'voucher_date': date.today(),
                            'post_date': date.today(),
                            'expense_id': None
                        })
                        st.session_state.booking_rows = rows
                        st.experimental_rerun()
                    if save:
                        if total_debit != total_credit:
                            st.error("借贷不平请检查！")
                        else:
                            try:
                                last_voucher = c.execute('SELECT MAX(voucher_no) FROM entry').fetchone()[0]
                                voucher_no = 100000 if last_voucher is None else last_voucher + 1
                                booking_date = date.today()
                                booked_expense_ids = set()
                                for r in rows:
                                    c.execute('''
                                        INSERT INTO expense_bookings (
                                            expense_id, booking_date, sap_account_code, sap_account_desc,
                                            sap_cost_center_code, sap_cost_center_desc, debit_amount,
                                            credit_amount, sap_employee_code, sap_employee_desc
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (
                                        r['expense_id'], booking_date,
                                        r['sap_account_code'], r['sap_account_desc'],
                                        r['sap_cost_center_code'], r['sap_cost_center_desc'],
                                        r['debit_amount'], r['credit_amount'],
                                        r['sap_employee_code'], r['sap_employee_desc']
                                    ))
                                    c.execute('''
                                        INSERT INTO entry (
                                            voucher_no, expense_id, entry_type, booking_date, sap_account_code, sap_account_desc,
                                            sap_cost_center_code, sap_cost_center_desc, debit_amount, credit_amount, sap_employee_code, sap_employee_desc,
                                            voucher_date, post_date
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (
                                        voucher_no, r['expense_id'], r['type'], booking_date, r['sap_account_code'], r['sap_account_desc'],
                                        r['sap_cost_center_code'], r['sap_cost_center_desc'], r['debit_amount'], r['credit_amount'],
                                        r['sap_employee_code'], r['sap_employee_desc'], r['voucher_date'], r['post_date']
                                    ))
                                    if r['expense_id']:
                                        booked_expense_ids.add(r['expense_id'])
                                for eid in booked_expense_ids:
                                    c.execute("UPDATE expenses SET status='booked' WHERE id=?", (eid,))
                                conn.commit()
                                st.session_state.voucher_modal = True
                                st.session_state.voucher_no = voucher_no
                            except Exception as e:
                                st.error(f"保存失败：{str(e)}")

elif st.session_state.current_page == "记账查看":
    st.title("📑 记账凭证查看")
    st.subheader("筛选条件")
    col1, col2, col3 = st.columns(3)
    with col1:
        voucher_no = st.text_input("凭证号")
        sap_account_code = st.text_input("SAP科目")
    with col2:
        min_amount = st.number_input("金额范围（从）", value=0.0, step=100.0)
        max_amount = st.number_input("金额范围（至）", value=0.0, step=100.0)
    with col3:
        employee = st.text_input("员工姓名")
        date_from = st.date_input("日期从", value=None, key="entry_date_from")
        date_to = st.date_input("日期至", value=None, key="entry_date_to")
    if st.button("🔍 查询"):
        query = "SELECT CAST(voucher_no AS TEXT) as '凭证号', entry_type as '借贷方', booking_date as '记账日期', sap_account_code as 'SAP科目', sap_account_desc as '科目描述', sap_cost_center_code as '成本中心', sap_cost_center_desc as '成本中心描述', debit_amount as '借方金额', credit_amount as '贷方金额', sap_employee_code as '员工代码', sap_employee_desc as '员工姓名', voucher_date as '凭证日期', post_date as '过账日期' FROM entry WHERE 1=1"
        params = []
        if voucher_no:
            query += " AND voucher_no=?"
            params.append(voucher_no)
        if sap_account_code:
            query += " AND sap_account_code LIKE ?"
            params.append(f"%{sap_account_code}%")
        if min_amount > 0:
            query += " AND (debit_amount >= ? OR credit_amount >= ?)"
            params.extend([min_amount, min_amount])
        if max_amount > 0:
            query += " AND (debit_amount <= ? OR credit_amount <= ?)"
            params.extend([max_amount, max_amount])
        if employee:
            query += " AND sap_employee_desc LIKE ?"
            params.append(f"%{employee}%")
        if date_from:
            query += " AND booking_date >= ?"
            params.append(str(date_from))
        if date_to:
            query += " AND booking_date <= ?"
            params.append(str(date_to))
        query += " ORDER BY voucher_no DESC, id ASC"
        df = pd.read_sql_query(query, conn, params=params)
        st.dataframe(df, use_container_width=True)
