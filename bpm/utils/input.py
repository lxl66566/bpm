from functools import wraps


def user_interrupt(func):
    """
    一个装饰器，用于捕获用户中断输入的异常，并打印提示信息。
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            print("canceled.")
            exit(0)
        except Exception as e:
            raise e

    return wrapper
