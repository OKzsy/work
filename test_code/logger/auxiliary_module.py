import logging

# spam_application是根记录器, 在辅助模块中创建spam_application的子记录器模块auxiliary,以及基于auxiliary的其他子模块
# 这样在辅助模块中的日志信息会传递会根记录器进行日志输出
# 子记录器将消息传播到与其父级记录器关联的处理器。因此，不必为应用程序使用的所有记录器定义和配置处理器。一般为顶级记录器配置处理器，
# 再根据需要创建子记录器就足够了。（但是，你可以通过将记录器的 propagate 属性设置为 False 来关闭传播。）
module_logger = logging.getLogger("spam_application.auxiliary")


class Auxiliary:
    def __init__(self):
        self.logger = logging.getLogger("spam_application.auxiliary.Auxiliary")
        self.logger.info("creating an instance of Auxiliary")

    def do_something(self):
        self.logger.info("doing something")
        a = 1 + 1
        self.logger.info("done doing something")


def some_function():
    module_logger.info('received a call to "some_function"')
