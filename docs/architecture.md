# 企业报销系统架构设计

## 1. 系统架构图

```mermaid
graph TD
    A[前端界面] --> B[Streamlit应用层]
    B --> C[业务逻辑层]
    C --> D[数据访问层]
    D --> E[SQLite数据库]
    
    subgraph 前端界面
    A1[登录界面] --> A2[报销采集]
    A2 --> A3[报销查看]
    A3 --> A4[主数据管理]
    A4 --> A5[用户角色管理]
    A5 --> A6[报销记账]
    A6 --> A7[记账查看]
    end
    
    subgraph 业务逻辑层
    C1[认证授权] --> C2[费用管理]
    C2 --> C3[主数据管理]
    C3 --> C4[记账管理]
    end
    
    subgraph 数据访问层
    D1[数据库连接] --> D2[ORM映射]
    D2 --> D3[数据迁移]
    end
```

## 2. 数据流图

```mermaid
sequenceDiagram
    participant U as 用户
    participant A as 应用层
    participant B as 业务层
    participant D as 数据层
    
    U->>A: 登录请求
    A->>B: 验证用户
    B->>D: 查询用户信息
    D-->>B: 返回用户数据
    B-->>A: 生成JWT令牌
    A-->>U: 返回令牌
    
    U->>A: 提交报销
    A->>B: 验证权限
    B->>D: 保存报销记录
    D-->>B: 确认保存
    B-->>A: 返回结果
    A-->>U: 显示结果
```

## 3. 模块交互说明

### 3.1 认证授权模块
- 负责用户登录验证
- 生成和验证JWT令牌
- 权限检查

### 3.2 费用管理模块
- 报销记录的CRUD操作
- 费用状态管理
- 数据验证

### 3.3 主数据管理模块
- 部门、公司、预算科目等基础数据维护
- 数据导入导出
- 数据关联管理

### 3.4 记账管理模块
- 生成记账凭证
- 借贷平衡检查
- 凭证状态管理

## 4. 数据库设计

### 4.1 核心表关系
```mermaid
erDiagram
    users ||--o{ expenses : creates
    roles ||--o{ users : has
    permissions ||--o{ role_permissions : has
    roles ||--o{ role_permissions : has
    expenses ||--o{ expense_bookings : generates
    expenses ||--o{ entry : generates
```

### 4.2 主要表说明
- users: 用户信息
- roles: 角色定义
- permissions: 权限定义
- expenses: 报销记录
- expense_bookings: 记账记录
- entry: 凭证分录
- config: 主数据配置

## 5. 安全设计

### 5.1 认证流程
1. 用户提交登录信息
2. 验证用户名密码
3. 生成JWT令牌
4. 令牌包含用户ID和角色信息

### 5.2 权限控制
1. 基于角色的访问控制
2. 细粒度的功能权限
3. 数据级别的权限控制

## 6. 部署架构

```mermaid
graph LR
    A[负载均衡器] --> B[应用服务器1]
    A --> C[应用服务器2]
    B --> D[数据库]
    C --> D
``` 