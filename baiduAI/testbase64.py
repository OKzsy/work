import base64
import urllib
import requests
from PIL import Image
from io import BytesIO

def get_file_content_as_base64(path, urlencoded=False):
    """
    获取文件base64编码
    :param path: 文件路径
    :param urlencoded: 是否对结果进行urlencoded 
    :return: base64编码信息
    """
    with open(path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf8")
        if urlencoded:
            content = urllib.parse.quote_plus(content)
    return content


def save_base64_content_to_file(base64_str, file_path):
    """
    获取文件base64编码
    :param path: 输出文件路径
    :return: None
    """
    img_data = base64.b64decode(base64_str)
    img = Image.open(BytesIO(img_data))
    img.save(file_path)
    return None


def main():
    src_img = "F:\SIFT\stinkbug.png"
    dst_img = "F:\SIFT\stinkbug_new.png"
    img_base64 = get_file_content_as_base64(src_img)
    save_base64_content_to_file(img_base64, dst_img)

    
    

if __name__ == '__main__':
    main()