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
        description TEXT,
        status TEXT DEFAULT 'pending'
    )
''')

# 创建配置表
c.execute('''
    CREATE TABLE IF NOT EXISTS config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        UNIQUE(key, value)
    )
''')

# 创建会计凭证表
c.execute('''
    CREATE TABLE IF NOT EXISTS account_entries (
        voucher_number INTEGER PRIMARY KEY,
        voucher_date DATE,
        post_date DATE,
        sap_account TEXT,
        sap_account_desc TEXT,
        cost_center TEXT,
        cost_center_desc TEXT,
        debit REAL,
        credit REAL,
        employee_code TEXT,
        employee_desc TEXT,
        expense_id INTEGER
    )
''')

# 创建用户表
c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
''')

# 初始化默认用户
c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", ("admin", "admin123", "admin"))
conn.commit()

# 初始化 session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if 'username' not in st.session_state:
    st.session_state.username = ""
    
if 'role' not in st.session_state:
    st.session_state.role = ""
    
if 'current_page' not in st.session_state:
    st.session_state.current_page = "报销采集"

# 登录界面
if not st.session_state.logged_in:
    st.title("🔐 登录系统")
    
    with st.form("login_form"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        submitted = st.form_submit_button("登录")
        
        if submitted:
            user = c.execute("SELECT username, password, role FROM users WHERE username=? AND password=?", 
                           (username, password)).fetchone()
            if user:
                st.session_state.logged_in = True
                st.session_state.username = user[0]
                st.session_state.role = user[2]
                st.success(f"欢迎回来，{user[0]}！")
                st.experimental_rerun()
            else:
                st.error("用户名或密码错误！")
    
    st.info("默认管理员账号: admin / 密码: admin123")
    st.stop()

# 页面选择
st.sidebar.title("导航")
page = st.sidebar.selectbox("选择页面", ["报销采集", "报销查看", "报销记账", "系统配置"])

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

elif page == "报销记账":
    st.title("📝 报销记账")

    # 查询待记账条目
    pending_df = pd.read_sql_query("SELECT * FROM expenses WHERE status='pending'", conn)
    
    if not pending_df.empty:
        selected_rows = st.data_editor(pending_df, key="pending_expenses", 
                                    column_config={"selected": st.column_config.CheckboxColumn("选择")})
        
        if st.button("生成会计凭证"):
            selected_ids = selected_rows[selected_rows["selected"]].id.tolist()
            if selected_ids:
                @st.dialog("会计凭证录入")
                def show_voucher_dialog(expense):
                    col1, col2 = st.columns(2)
                    with col1:
                        voucher_date = st.date_input("凭证日期")
                        sap_account = st.text_input("SAP核算科目")
                    with col2:
                        post_date = st.date_input("过账日期")
                        sap_cost_center = st.text_input("SAP成本中心编码")
                    
                    # 借方金额自动填充
                    debit_amount = expense.amount
                    st.markdown("### 会计分录")
                    entries = []
                    
                    # 借方行
                    entries.append({
                        "行标": "借方",
                        "凭证日期": voucher_date,
                        "过账日期": post_date,
                        "SAP核算科目": sap_account,
                        "SAP核算科目描述": "费用报销",
                        "SAP成本中心编码": sap_cost_center,
                        "SAP成本中心描述": "成本中心",
                        "借方金额": debit_amount,
                        "贷方金额": 0.0,
                        "员工编码": expense.employee,
                        "员工描述": expense.employee
                    })
                    
                    # 贷方行（可添加多行）
                    if 'credit_entries' not in st.session_state:
                        st.session_state.credit_entries = []
                    
                    for i, entry in enumerate(st.session_state.credit_entries):
                        cols = st.columns([1, 3, 3, 2, 2, 2, 2, 2, 2])
                        with cols[0]:
                            st.write(f"{i+1}. 贷方")
                        with cols[1]:
                            entry["SAP核算科目"] = st.text_input(f"科目_{i}", value=entry.get("SAP核算科目", ""))
                        with cols[2]:
                            entry["SAP核算科目描述"] = st.text_input(f"科目描述_{i}", value=entry.get("SAP核算科目描述", ""))
                        with cols[3]:
                            entry["SAP成本中心编码"] = st.text_input(f"成本中心_{i}", value=entry.get("SAP成本中心编码", ""))
                        with cols[4]:
                            entry["SAP成本中心描述"] = st.text_input(f"成本中心描述_{i}", value=entry.get("SAP成本中心描述", ""))
                        with cols[5]:
                            entry["借方金额"] = st.number_input(f"借方_{i}", value=0.0, disabled=True)
                        with cols[6]:
                            entry["贷方金额"] = st.number_input(f"贷方_{i}", value=entry.get("贷方金额", 0.0))
                        with cols[7]:
                            entry["员工编码"] = st.text_input(f"员工编码_{i}", value=entry.get("员工编码", ""))
                        with cols[8]:
                            entry["员工描述"] = st.text_input(f"员工描述_{i}", value=entry.get("员工描述", ""))
                    
                    # 添加新行按钮
                    if st.button("➕ 添加行"):
                        st.session_state.credit_entries.append({})
                        st.rerun()
                    
                    # 合计计算
                    total_debit = debit_amount
                    total_credit = sum(e.get("贷方金额", 0) for e in st.session_state.credit_entries)
                    
                    cols = st.columns([7, 2, 2])
                    with cols[0]:
                        st.markdown("**合计**")
                    with cols[1]:
                        st.markdown(f"**￥{total_debit:.2f}**")
                    with cols[2]:
                        st.markdown(f"**￥{total_credit:.2f}****")
                    
                    if st.button("✅ 保存凭证"):
                        if abs(total_debit - total_credit) > 0.01:
                            st.error("借贷不平，请检查！")
                        else:
                            # 获取当前最大凭证号
                            c.execute("SELECT MAX(voucher_number) FROM account_entries")
                            max_voucher = c.fetchone()[0] or 10000000
                            
                            # 保存会计分录
                            for entry in entries + st.session_state.credit_entries:
                                c.execute('''
                                    INSERT INTO account_entries (
                                        voucher_number, voucher_date, post_date, 
                                        sap_account, sap_account_desc,
                                        cost_center, cost_center_desc,
                                        debit, credit, employee_code, employee_desc, expense_id
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ''', (
                                    max_voucher + 1,
                                    voucher_date, post_date,
                                    sap_account, "费用报销",
                                    sap_cost_center, "成本中心",
                                    debit_amount, 0.0,
                                    expense.employee, expense.employee,
                                    expense.id
                                ))
                            
                            # 更新费用记录状态
                            c.execute(f"UPDATE expenses SET status='posted' WHERE id IN ({','.join(map(str, selected_ids))})")
                            conn.commit()
                            st.success(f"凭证 {max_voucher + 1} 已生成！")
                            st.session_state.credit_entries = []
                            st.rerun()
                
                # 显示对话框
                for idx, row in pending_df.iterrows():
                    if row.id in selected_ids:
                        show_voucher_dialog(row)
            else:
                st.warning("请先选择要记账的条目")
    else:
        st.info("暂无待记账条目")

elif page == "系统配置":
    st.title("🔧 系统配置")

    config_tabs = st.tabs(["部门", "公司", "预算科目", "报销人", "用户管理"])
    
    with config_tabs[4]:
        st.subheader("用户管理")
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input("用户名")
            password = st.text_input("密码", type="password")
        with col2:
            role = st.selectbox("角色", ["admin", "accountant", "user"])
            module_access = st.multiselect("模块权限", ["报销采集", "报销查看", "报销记账"])
            
        if st.button("添加用户") and username and password:
            try:
                c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                          (username, password, ','.join(module_access)))
                conn.commit()
                st.success(f"用户 {username} 已添加！")
            except sqlite3.IntegrityError:
                st.warning(f"用户名 {username} 已存在！")
