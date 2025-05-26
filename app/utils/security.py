import bcrypt
import jwt
from datetime import datetime, timedelta
from config import config
from app.utils.logger import logger

def hash_password(password):
    """对密码进行哈希处理"""
    try:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except Exception as e:
        logger.error(f"密码哈希处理失败: {str(e)}")
        raise

def verify_password(password, hashed):
    """验证密码"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        logger.error(f"密码验证失败: {str(e)}")
        return False

def generate_token(user_id, role):
    """生成JWT令牌"""
    try:
        payload = {
            'user_id': user_id,
            'role': role,
            'exp': datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(payload, config['default'].SECRET_KEY, algorithm='HS256')
        return token
    except Exception as e:
        logger.error(f"令牌生成失败: {str(e)}")
        raise

def verify_token(token):
    """验证JWT令牌"""
    try:
        payload = jwt.decode(token, config['default'].SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("令牌已过期")
        return None
    except jwt.InvalidTokenError as e:
        logger.error(f"无效的令牌: {str(e)}")
        return None

def check_permission(user_role, required_permission):
    """检查用户权限"""
    try:
        # 这里需要实现具体的权限检查逻辑
        # 可以从数据库查询用户角色的权限
        return True
    except Exception as e:
        logger.error(f"权限检查失败: {str(e)}")
        return False 