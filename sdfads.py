import cv2
import numpy as np
import PySimpleGUI as sg
import pyperclip
from PIL import ImageGrab, Image
import re
from ctypes import windll
 
sg.theme('LightBlue2')
user32 = windll.user32
screen_width = user32.GetSystemMetrics(0)
screen_height = user32.GetSystemMetrics(1)
 
crop_result = None
 
def decode_qr_cv2(img):
    qr_detector = cv2.QRCodeDetector()
    data, bbox, _ = qr_detector.detectAndDecode(img)
    return data if data else None
 
def preprocess_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 3)
    _, binary = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary
 
def mouse_event(event, x, y, flags, param):
    global ix, iy, drawing, img_copy, full_screen, crop_result
    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix, iy = x, y
    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            img_copy = full_screen.copy()
            cv2.rectangle(img_copy, (ix, iy), (x, y), (0, 255, 0), 2)
    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        x1, y1 = min(ix, x), min(iy, y)
        x2, y2 = max(ix, x), max(iy, y)
        if x2 - x1 > 10 and y2 - y1 > 10:
            crop_img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            crop_result = cv2.cvtColor(np.array(crop_img), cv2.COLOR_RGB2BGR)
        cv2.destroyAllWindows()
 
def screen_capture():
    global ix, iy, drawing, img_copy, full_screen, crop_result
    ix, iy = -1, -1
    drawing = False
    crop_result = None
 
    full_screen = np.array(ImageGrab.grab(bbox=(0, 0, screen_width, screen_height)))
    full_screen = cv2.cvtColor(full_screen, cv2.COLOR_RGB2BGR)
    img_copy = full_screen.copy()
 
    alpha = 0.3
    overlay = full_screen.copy()
    cv2.addWeighted(overlay, alpha, full_screen, 1 - alpha, 0, full_screen)
 
    cv2.namedWindow("screen_capture", cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty("screen_capture", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.setMouseCallback("screen_capture", mouse_event)
 
    while True:
        cv2.imshow("screen_capture", img_copy)
        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            crop_result = None
            break
        if cv2.getWindowProperty("screen_capture", cv2.WND_PROP_VISIBLE) < 1:
            break
 
    cv2.destroyAllWindows()
    return crop_result
 
def decode_qr_from_capture():
    try:
        img = screen_capture()
        if img is None:
            return None, "已取消截图"
        processed = preprocess_image(img)
        data = decode_qr_cv2(processed) or decode_qr_cv2(img)
        if data:
            return data, "&#9989; 识别成功"
        else:
            return None, "&#10060; 未检测到二维码"
    except Exception as e:
        return None, f"错误：{str(e)}"
 
def decode_qr_from_image(img_path):
    try:
        # 方案一（保持原样，如果路径有中文会失败）：
        # img = cv2.imread(img_path)
        
        # 方案二（使用 PIL 读取，完美支持中文路径）：
        from PIL import Image
        img_pil = Image.open(img_path)
        if img_pil.mode != 'RGB':
            img_pil = img_pil.convert('RGB')
        img = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

        if img is None:
            return None, "&#10060; 无法读取图片"
        processed = preprocess_image(img)
        data = decode_qr_cv2(processed) or decode_qr_cv2(img)
        return (data, "&#9989; 识别成功") if data else (None, "&#10060; 未检测到二维码")
    except Exception as e:
        return None, f"错误：{str(e)}"
 
def parse_baidu_link(text):
    result = {"link": "", "code": ""}
    link_match = re.search(r'https://pan\.baidu\.com/[^\s]+', text)
    if link_match:
        result["link"] = link_match.group(0)
 
    pwd_match = re.search(r'pwd=([A-Za-z0-9]{4})', text)
    if pwd_match:
        result["code"] = pwd_match.group(1).upper()
    else:
        code_match = re.search(r'[提取码]*[:：]\s*([A-Za-z0-9]{4})', text)
        if code_match:
            result["code"] = code_match.group(1).upper()
    return result
 
layout = [
    [sg.Text("百度网盘二维码识别工具", font=("微软雅黑", 14, "bold"))],
    [sg.HorizontalSeparator()],
    [sg.Button("选择图片识别", size=(15, 1)),
     sg.Button("屏幕截图识别", size=(15, 1))],
    [sg.Text("_" * 50)],
    [sg.Text("识别结果：")],
    [sg.Multiline(size=(50, 4), key="-RESULT-", disabled=True)],
    [sg.Text("网盘链接："), sg.Input(key="-LINK-", size=(40, 1), disabled=True)],
    [sg.Text("提取码："), sg.Input(key="-CODE-", size=(10, 1), disabled=True), sg.Button("复制全部")],
    [sg.Text("", key="-STATUS-", text_color="red", size=(50, 1))]
]
 
window = sg.Window("百度网盘二维码识别", layout)
 
while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED:
        break
 
    if event == "选择图片识别":
        file_path = sg.popup_get_file("选择二维码图片", file_types=(("图片", "*.png;*.jpg;*.jpeg;*.bmp"),))
        if file_path:
            qr_data, status = decode_qr_from_image(file_path)
            window["-STATUS-"].update(status)
            if qr_data:
                window["-RESULT-"].update(qr_data)
                bd = parse_baidu_link(qr_data)
                window["-LINK-"].update(bd["link"])
                window["-CODE-"].update(bd["code"])
 
    if event == "屏幕截图识别":
        window.Hide()
        qr_data, status = decode_qr_from_capture()
        window.UnHide()
        window["-STATUS-"].update(status)
        if qr_data:
            window["-RESULT-"].update(qr_data)
            bd = parse_baidu_link(qr_data)
            window["-LINK-"].update(bd["link"])
            window["-CODE-"].update(bd["code"])
 
    if event == "复制全部":
        link = values["-LINK-"]
        code = values["-CODE-"]
        if link and code:
            pyperclip.copy(f"链接：{link}\n提取码：{code}")
            window["-STATUS-"].update("&#9989; 已复制到剪贴板")
        elif link:
            pyperclip.copy(link)
            window["-STATUS-"].update("&#9989; 已复制链接")
 
window.close()