import pytest
from datetime import date
from app.models.database import db
from app.utils.security import hash_password

@pytest.fixture
def test_db():
    """创建测试数据库"""
    db._instance = None
    db._initialize()
    yield db
    # 清理测试数据
    with db.get_connection() as conn:
        conn.execute("DELETE FROM expenses")
        conn.execute("DELETE FROM users")
        conn.commit()

def test_create_expense(test_db):
    """测试创建费用记录"""
    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO expenses (
                expense_date, department, company, budget_item,
                employee, amount, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            date.today(), 'DEPT001', 'COMP001',
            'BUDGET001', 'EMP001', 100.00, '测试费用'
        ))
        conn.commit()
        
        # 验证记录是否创建成功
        cursor.execute("SELECT * FROM expenses WHERE description = ?", ('测试费用',))
        result = cursor.fetchone()
        assert result is not None
        assert result['amount'] == 100.00
        assert result['status'] == 'pending'

def test_update_expense(test_db):
    """测试更新费用记录"""
    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        # 创建测试记录
        cursor.execute('''
            INSERT INTO expenses (
                expense_date, department, company, budget_item,
                employee, amount, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            date.today(), 'DEPT001', 'COMP001',
            'BUDGET001', 'EMP001', 100.00, '测试费用'
        ))
        conn.commit()
        
        # 更新记录
        cursor.execute('''
            UPDATE expenses
            SET amount = ?, description = ?
            WHERE description = ?
        ''', (200.00, '更新后的费用', '测试费用'))
        conn.commit()
        
        # 验证更新是否成功
        cursor.execute("SELECT * FROM expenses WHERE description = ?", ('更新后的费用',))
        result = cursor.fetchone()
        assert result is not None
        assert result['amount'] == 200.00

def test_delete_expense(test_db):
    """测试删除费用记录"""
    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        # 创建测试记录
        cursor.execute('''
            INSERT INTO expenses (
                expense_date, department, company, budget_item,
                employee, amount, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            date.today(), 'DEPT001', 'COMP001',
            'BUDGET001', 'EMP001', 100.00, '测试费用'
        ))
        conn.commit()
        
        # 删除记录
        cursor.execute("DELETE FROM expenses WHERE description = ?", ('测试费用',))
        conn.commit()
        
        # 验证删除是否成功
        cursor.execute("SELECT * FROM expenses WHERE description = ?", ('测试费用',))
        result = cursor.fetchone()
        assert result is None 