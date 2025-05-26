import sqlite3
from contextlib import contextmanager
from config import config
from app.utils.logger import logger

class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.db_path = config['default'].DATABASE_URL.replace('sqlite:///', '')
        self._create_tables()
    
    @contextmanager
    def get_connection(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            yield conn
        except Exception as e:
            logger.error(f"数据库连接错误: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()
    
    def _create_tables(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建费用记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    expense_date DATE,
                    department TEXT,
                    company TEXT,
                    budget_item TEXT,
                    employee TEXT,
                    amount REAL,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建配置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL,
                    code TEXT NOT NULL,
                    description TEXT NOT NULL,
                    sap_code TEXT NOT NULL,
                    sap_description TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(key, code, description)
                )
            ''')
            
            # 创建角色表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role_name TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(role_name)
                )
            ''')
            
            # 创建权限表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module_name TEXT NOT NULL,
                    permission_name TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(module_name, permission_name)
                )
            ''')
            
            # 创建角色权限关联表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS role_permissions (
                    role_id INTEGER,
                    permission_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (role_id) REFERENCES roles (id),
                    FOREIGN KEY (permission_id) REFERENCES permissions (id),
                    PRIMARY KEY (role_id, permission_id)
                )
            ''')
            
            # 创建用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    password TEXT NOT NULL,
                    role_id INTEGER,
                    company_code TEXT,
                    department_code TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    FOREIGN KEY (role_id) REFERENCES roles (id),
                    UNIQUE(user_id)
                )
            ''')
            
            # 创建记账记录表
            cursor.execute('''
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (expense_id) REFERENCES expenses (id)
                )
            ''')
            
            # 创建entry表
            cursor.execute('''
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
                    post_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            logger.info("数据库表创建成功")

# 创建全局数据库实例
db = Database() 