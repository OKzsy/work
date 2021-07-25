# -*- coding:utf-8 -*-


import sys


class BuildXml():
    def __init__(self, filename=None):
        self.filename = filename
        self.__get_f = None
        pass

    def openfile(self):
        if self.filename == None:
            print('没有提供文件名！在建立实例时，请提供创建文件的名称！')
            return False
        try:
            self.__get_f = open(self.filename, 'a', encoding='utf-8')
            return True
        except:
            print('打开{}文件有问题'.format(self.filename))
            return False

    def write_xml(self, level, element):
        try:
            if level == 0:
                self.__get_f.write(element + '\n')
            else:
                self.__get_f.write(' ' * 2 ** (level + 1) + element + '\n')
        except:
            print('往{}文件写{}出错'.format(self.filename, element))
            pass

    def close_xml(self):
        if self.__get_f:
            self.__get_f.close()


def main():
    filename = r'E:\PythonCode\pic\storehouse.xml'
    flag = False
    content = {
        1:[0,'<storehouse>'],
        2:[1,'<goods category="fish">'],
        3:[2,'<title>淡水鱼</title>'],
        4:[2,'<name>鲫鱼</name>'],
        5:[2,'<amount>18</amount>'],
        6:[2,'<price>8</price>'],
        7:[1,'</goods>'],
        8:[1,'<goods category="fruit">'],
        9:[2,'<title>温带水果</title>'],
        10:[2,'<name>猕猴桃</name>'],
        11:[2,'<amount>10</amount>'],
        12:[2,'<price>10</price>'],
        13:[1,'</goods>'],
        14:[0,'</storehouse>']
    }
    oxml = BuildXml(filename)
    try:
        if oxml.openfile():
            for get_item in content.items():
                oxml.write_xml(get_item[1][0], get_item[1][1])
            flag = True
    except:
        print('写入出错')
        sys.exit()
        pass
    finally:
        if flag:
            oxml.close_xml()
            print('往{}文件写入成功'.format(filename))


if __name__ == '__main__':
    main()
