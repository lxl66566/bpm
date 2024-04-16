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


@user_interrupt
def user_input(s: str):
    """
    获取用户输入，并返回。
    """
    return input(s)


@user_interrupt
def get_user_choice_classic(options: list[str], title="select by id:"):
    # 打印选项列表
    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")

    # 获取用户输入
    user_input_value = input(title)

    # 验证用户输入
    while (
        not user_input_value.isdigit()
        or int(user_input_value) < 1
        or int(user_input_value) > len(options)
    ):
        user_input_value = input("Invalid input: please input a valid number.")

    return int(user_input_value) - 1
