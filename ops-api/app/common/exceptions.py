class AppError(Exception):
    def __init__(self, message: str, code: int, status_code: int, data: dict | None = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.data = data
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "资源不存在", data: dict | None = None):
        super().__init__(message=message, code=404, status_code=404, data=data)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "未认证或 Token 无效"):
        super().__init__(message=message, code=401, status_code=401)


class ConflictError(AppError):
    def __init__(self, message: str, data: dict | None = None):
        super().__init__(message=message, code=409, status_code=409, data=data)


class BadRequestError(AppError):
    def __init__(self, message: str, data: dict | None = None):
        super().__init__(message=message, code=400, status_code=400, data=data)


class ForbiddenError(AppError):
    def __init__(self, message: str = "无权限访问"):
        super().__init__(message=message, code=403, status_code=403)
