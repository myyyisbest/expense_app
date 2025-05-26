# 企业报销系统

这是一个基于Streamlit开发的企业报销管理系统，用于管理公司的费用报销流程。

## 功能特点

- 用户认证和授权
- 费用报销记录管理
- 主数据管理（部门、公司、预算科目等）
- 报销记账功能
- 凭证管理
- 数据导出功能

## 技术栈

- Python 3.9+
- Streamlit
- SQLite
- SQLAlchemy
- JWT认证
- bcrypt密码加密

## 安装说明

1. 克隆项目
```bash
git clone [项目地址]
cd expense_app
```

2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置环境变量
复制`.env.example`文件为`.env`，并填写相应的配置信息。

5. 初始化数据库
```bash
python -m alembic upgrade head
```

6. 初始化示例数据
```bash
python scripts/init_data.py
```

7. 运行应用
```bash
streamlit run app.py
```

## 示例数据

系统预置了以下示例数据：

### 测试账号
- 管理员：admin / admin123
- 部门经理：manager1 / manager123
- 普通员工：employee1 / employee123
- 财务人员：finance1 / finance123

### 主数据
- 部门：财务部、人事部、IT部、市场部、销售部
- 公司：总公司、分公司A、分公司B
- 预算科目：差旅费、办公用品、业务招待费、培训费、通讯费
- 员工：张三、李四、王五、赵六、钱七

### 示例报销记录
- 差旅费报销：1000元
- 办公用品：500元
- 业务招待：2000元

## 项目结构

```
expense_app/
├── app/                    # 应用主目录
│   ├── models/            # 数据模型
│   ├── views/             # 视图
│   ├── controllers/       # 控制器
│   ├── utils/             # 工具函数
│   └── static/            # 静态文件
├── config/                # 配置文件
├── docs/                  # 文档
│   └── architecture.md    # 架构设计文档
├── scripts/               # 脚本文件
│   └── init_data.py      # 示例数据初始化
├── tests/                 # 测试文件
├── migrations/            # 数据库迁移
├── logs/                  # 日志文件
├── requirements.txt       # 依赖管理
└── README.md             # 项目说明
```

## 开发指南

1. 代码风格
- 使用black进行代码格式化
- 使用flake8进行代码检查
- 使用mypy进行类型检查

2. 测试
```bash
pytest tests/
```

3. 数据库迁移
```bash
# 创建迁移
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head
```

## 部署说明

1. 生产环境配置
- 修改`.env`文件中的配置
- 设置`DEBUG=False`
- 配置适当的日志级别

2. 数据库备份
- 定期备份SQLite数据库文件
- 建议使用专业的数据库备份工具

## 安全说明

- 所有密码都经过bcrypt加密存储
- 使用JWT进行身份验证
- 实现了基于角色的访问控制
- 敏感配置信息通过环境变量管理

## 贡献指南

1. Fork项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证

MIT License
