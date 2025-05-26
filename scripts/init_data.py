import sqlite3
from datetime import date
from app.utils.security import hash_password

def init_database():
    """初始化示例数据"""
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    
    # 初始化部门数据
    departments = [
        ('DEPT001', '财务部', 'CC001', '财务成本中心'),
        ('DEPT002', '人事部', 'CC002', '人事成本中心'),
        ('DEPT003', 'IT部', 'CC003', 'IT成本中心'),
        ('DEPT004', '市场部', 'CC004', '市场成本中心'),
        ('DEPT005', '销售部', 'CC005', '销售成本中心')
    ]
    
    for dept in departments:
        c.execute('''
            INSERT OR IGNORE INTO config (key, code, description, sap_code, sap_description)
            VALUES (?, ?, ?, ?, ?)
        ''', ('department', dept[0], dept[1], dept[2], dept[3]))
    
    # 初始化公司数据
    companies = [
        ('COMP001', '总公司', 'C001', '总公司'),
        ('COMP002', '分公司A', 'C002', '分公司A'),
        ('COMP003', '分公司B', 'C003', '分公司B')
    ]
    
    for comp in companies:
        c.execute('''
            INSERT OR IGNORE INTO config (key, code, description, sap_code, sap_description)
            VALUES (?, ?, ?, ?, ?)
        ''', ('company', comp[0], comp[1], comp[2], comp[3]))
    
    # 初始化预算科目
    budget_items = [
        ('BUDGET001', '差旅费', 'A001', '差旅费'),
        ('BUDGET002', '办公用品', 'A002', '办公用品'),
        ('BUDGET003', '业务招待费', 'A003', '业务招待费'),
        ('BUDGET004', '培训费', 'A004', '培训费'),
        ('BUDGET005', '通讯费', 'A005', '通讯费')
    ]
    
    for budget in budget_items:
        c.execute('''
            INSERT OR IGNORE INTO config (key, code, description, sap_code, sap_description)
            VALUES (?, ?, ?, ?, ?)
        ''', ('budget_item', budget[0], budget[1], budget[2], budget[3]))
    
    # 初始化员工数据
    employees = [
        ('EMP001', '张三', 'E001', '张三'),
        ('EMP002', '李四', 'E002', '李四'),
        ('EMP003', '王五', 'E003', '王五'),
        ('EMP004', '赵六', 'E004', '赵六'),
        ('EMP005', '钱七', 'E005', '钱七')
    ]
    
    for emp in employees:
        c.execute('''
            INSERT OR IGNORE INTO config (key, code, description, sap_code, sap_description)
            VALUES (?, ?, ?, ?, ?)
        ''', ('employee', emp[0], emp[1], emp[2], emp[3]))
    
    # 初始化角色
    roles = [
        ('admin', '系统管理员'),
        ('manager', '部门经理'),
        ('employee', '普通员工'),
        ('finance', '财务人员')
    ]
    
    for role in roles:
        c.execute('''
            INSERT OR IGNORE INTO roles (role_name, description)
            VALUES (?, ?)
        ''', role)
    
    # 初始化权限
    permissions = [
        ('expense', 'create', '创建报销记录'),
        ('expense', 'view', '查看报销记录'),
        ('expense', 'export', '导出报销记录'),
        ('expense', 'book', '报销记账'),
        ('master_data', 'manage', '管理主数据'),
        ('user', 'manage', '管理用户'),
        ('role', 'manage', '管理角色')
    ]
    
    for perm in permissions:
        c.execute('''
            INSERT OR IGNORE INTO permissions (module_name, permission_name, description)
            VALUES (?, ?, ?)
        ''', perm)
    
    # 初始化管理员用户
    admin_role_id = c.execute("SELECT id FROM roles WHERE role_name='admin'").fetchone()[0]
    c.execute('''
        INSERT OR IGNORE INTO users (user_id, user_name, password, role_id)
        VALUES (?, ?, ?, ?)
    ''', ('admin', '管理员', hash_password('admin123'), admin_role_id))
    
    # 初始化测试用户
    test_users = [
        ('manager1', '经理A', 'manager123', 'manager'),
        ('employee1', '员工A', 'employee123', 'employee'),
        ('finance1', '财务A', 'finance123', 'finance')
    ]
    
    for user in test_users:
        role_id = c.execute("SELECT id FROM roles WHERE role_name=?", (user[3],)).fetchone()[0]
        c.execute('''
            INSERT OR IGNORE INTO users (user_id, user_name, password, role_id)
            VALUES (?, ?, ?, ?)
        ''', (user[0], user[1], hash_password(user[2]), role_id))
    
    # 初始化示例报销记录
    expenses = [
        (date.today(), 'DEPT001', 'COMP001', 'BUDGET001', 'EMP001', 1000.00, '差旅费报销'),
        (date.today(), 'DEPT002', 'COMP001', 'BUDGET002', 'EMP002', 500.00, '办公用品'),
        (date.today(), 'DEPT003', 'COMP002', 'BUDGET003', 'EMP003', 2000.00, '业务招待')
    ]
    
    for exp in expenses:
        c.execute('''
            INSERT INTO expenses (expense_date, department, company, budget_item, employee, amount, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', exp)
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_database()
    print("示例数据初始化完成！") 