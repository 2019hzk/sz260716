"""
职责：负责处理认证信息
"""
import jwt
from fastapi import HTTPException, status

from atguigu.app.schemas import CurrentUser
from atguigu.common.settings import get_settings


def authorized_user(authorization: str | None, *require_role: str) -> CurrentUser:
    """
     职责: 对用户身份做鉴权
     1. 鉴权判断用户身份信息是否携带了，以及携带的格式是否正确
     2. 鉴权判断身份信息的用户角色是否满足接口的要求，如果满足，直接返回认证后的对象，否则抛出异常
    :param authorization: 前端请求携带的认证信息
    :param require_role: 接口要求的权限【"user","staff","admin"】
    :return: 返回认证后的用户信息
    """

    # 1、判断用户认证信息是否携带了
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户身份认证失败")

    # 2. 获取令牌
    access_token = authorization.split(" ", 1)[1]

    # 3. 从认证信息中获取用户信息
    current_user = decode_access_token(access_token)

    # 4. 当前用户角色是否满足接口要求
    if current_user.role not in require_role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="暂无访问接口资源的权限")

    # 5. 返回认证后的用户信息
    return current_user


def decode_access_token(access_token: str) -> CurrentUser:
    """
    职责：根据令牌获取用户身份信息
    :param access_token:
    :return:
    """

    user_info_dict = jwt.decode(access_token, key=get_settings().jwt_secret, algorithms=[get_settings().jwt_algorithm])

    return CurrentUser.model_validate(user_info_dict)


def encode_access_token(user_id: str) -> str:
    """
    职责：生成用户令牌
    :return:
    """
