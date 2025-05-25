import streamlit as st
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
        description TEXT
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

# 创建用户表
c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        user_name TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        UNIQUE(user_id)
    )
''')

# 确保至少有一个管理员用户
admin_exists = c.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]
if admin_exists == 0:
    c.execute("INSERT OR IGNORE INTO users (user_id, user_name, password, role) VALUES (?, ?, ?, ?)", 
              ("admin", "管理员", "admin123", "admin"))
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
            user = c.execute("SELECT user_id, user_name, role FROM users WHERE user_id=? AND password=?", 
                           (user_id, password)).fetchone()
            if user:
                st.session_state.logged_in = True
                st.session_state.user_id = user[0]
                st.session_state.user_role = user[2]
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

# 创建导航按钮
col1, col2 = st.sidebar.columns([1,1])
with col1:
    if st.button("📝 采集"):
        st.session_state.current_page = "报销采集"
with col2:
    if st.button("🔍 查看"):
        st.session_state.current_page = "报销查看"

# 只有管理员才能看到配置按钮
if st.session_state.user_role == "admin":
    if st.sidebar.button("⚙️ 配置"):
        st.session_state.current_page = "配置管理"

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
        employee = st.selectbox("报销人", 
            [row[1] for row in c.execute("SELECT code, description FROM config WHERE key='employee'")])
        amount = st.number_input("金额", min_value=0.00, step=0.00)
        description = st.text_input("摘要 / 说明")

        submitted = st.form_submit_button("提交")
        if submitted:
            # 获取选中项的编码
            dept_code = c.execute("SELECT code FROM config WHERE key='department' AND description=?", (department,)).fetchone()[0]
            comp_code = c.execute("SELECT code FROM config WHERE key='company' AND description=?", (company,)).fetchone()[0]
            budget_code = c.execute("SELECT code FROM config WHERE key='budget_item' AND description=?", (budget_item,)).fetchone()[0]
            emp_code = c.execute("SELECT code FROM config WHERE key='employee' AND description=?", (employee,)).fetchone()[0]
            
            c.execute('''
                INSERT INTO expenses (expense_date, department, company, budget_item, employee, amount, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
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

    # 金额区间筛选
    amount_col1, amount_col2 = st.columns(2)
    with amount_col1:
        min_amount = st.number_input("金额范围（从）", value=0.0, step=100.0)
    with amount_col2:
        max_amount = st.number_input("金额范围（至）", value=0.0, step=100.0)
    
    if max_amount > 0 and max_amount < min_amount:
        st.warning("最大金额不能小于最小金额")
        max_amount = min_amount

    # 添加搜索按钮
    search_clicked = st.button("🔍 执行搜索")

    # 构建查询
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

elif st.session_state.current_page == "配置管理":
    st.title("🔧 配置管理")
    # 配置管理界面
    # 将配置管理拆分为主数据管理和用户管理
    main_config_tabs = st.tabs(["主数据管理", "用户管理"]) # 顶级标签页

    with main_config_tabs[0]: # 主数据管理
        st.subheader("主数据管理")
        config_tabs = st.tabs(["部门", "公司", "预算科目", "报销人"]) # 主数据下的子标签页

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
        st.subheader("报销人管理") # 之前的员工管理改为报销人管理，与前面统一
        # 手动添加部分
        col1, col2 = st.columns(2)
        with col1:
            code = st.text_input("报销人编码")
            sap_code = st.text_input("SAP员工代码", value=code) # 统一为SAP员工代码
        with col2:
            desc = st.text_input("报销人姓名")
            sap_desc = st.text_input("SAP员工姓名", value=desc) # 统一为SAP员工姓名
        if st.button("添加报销人") and code and desc: # 按钮文字统一
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

    with main_config_tabs[1]: # 用户管理
        st.subheader("用户管理")
        # 手动添加用户部分
        col1, col2, col3 = st.columns(3)
        with col1:
            new_user_id = st.text_input("用户ID (用户管理)") # 增加key防止冲突
        with col2:
            new_user_name = st.text_input("用户姓名 (用户管理)")
        with col3:
            new_user_password = st.text_input("密码 (用户管理)", type="password")
        new_user_role = st.selectbox("用户角色 (用户管理)", ["user", "admin"], key="user_role_select")
        if st.button("添加用户") and new_user_id and new_user_name and new_user_password:
            try:
                c.execute("INSERT OR IGNORE INTO users (user_id, user_name, password, role) VALUES (?, ?, ?, ?)", 
                        (new_user_id, new_user_name, new_user_password, new_user_role))
                conn.commit()
                st.success(f"用户 '{new_user_name}({new_user_id})' 已添加！")
            except sqlite3.IntegrityError:
                st.warning(f"用户ID {new_user_id} 已存在！")

        # Excel导入用户部分
        st.divider()
        st.subheader("批量导入用户")
        col1_user_import, col2_user_import = st.columns([3, 1])
        with col1_user_import:
            user_uploaded_file = st.file_uploader("上传用户Excel文件", type=["xlsx"], key="user_uploader")
        with col2_user_import:
            user_template = create_excel_template(["用户ID", "用户姓名", "密码", "角色"])
            st.download_button(
                label="📥 下载用户模板",
                data=user_template,
                file_name="用户导入模板.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="user_template_download"
            )
        if user_uploaded_file is not None:
            try:
                user_df_import = pd.read_excel(user_uploaded_file)
                if all(col in user_df_import.columns for col in ["用户ID", "用户姓名", "密码", "角色"]):
                    for _, row in user_df_import.iterrows():
                        try:
                            c.execute("INSERT OR IGNORE INTO users (user_id, user_name, password, role) VALUES (?, ?, ?, ?)",
                                    (row["用户ID"], row["用户姓名"], row["密码"], row["角色"]))
                        except sqlite3.IntegrityError:
                            continue
                    conn.commit()
                    st.success("用户Excel数据导入成功！")
                else:
                    st.error("用户Excel文件格式不正确！请确保包含：用户ID、用户姓名、密码、角色")
            except Exception as e:
                st.error(f"用户导入失败：{str(e)}")

        # 显示用户列表
        st.divider()
        st.subheader("用户列表")
        users_df = pd.read_sql_query("SELECT user_id AS 用户ID, user_name AS 用户姓名, role AS 角色 FROM users ORDER BY user_id", conn)
        st.dataframe(users_df)

    # 已将用户管理功能移至顶层标签页，此处无需重复代码
    # 原有的显示整个config表的部分已注释，因为数据已在各自的tab中显示
