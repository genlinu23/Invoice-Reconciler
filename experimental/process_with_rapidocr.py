"""
发票整理工具 - RapidOCR + LLM版本
使用RapidOCR提取文本，保存OCR结果用于debug
"""
import os
import sys
import io
import json
import base64
import requests
from pathlib import Path
from shutil import copy2
from dotenv import load_dotenv
from datetime import datetime

# 设置UTF-8输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 导入RapidOCR
try:
    from rapidocr_onnxruntime import RapidOCR
    RAPIDOCR_AVAILABLE = True
except ImportError:
    RAPIDOCR_AVAILABLE = False
    print("[WARNING] RapidOCR未安装，将使用纯视觉模型")

# PDF支持
try:
    from pdf2image import convert_from_path
    from PIL import Image
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# 加载环境变量
load_dotenv()
API_URL = os.getenv("API_BASE_URL", "http://45.120.102.120:10021/v1/chat/completions")
API_KEY = os.getenv("API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen3-VL-235B-A22B-Instruct-FP8")

# OCR实例（单例）
_ocr_instance = None


def get_ocr_instance():
    """获取RapidOCR实例"""
    global _ocr_instance
    if _ocr_instance is None and RAPIDOCR_AVAILABLE:
        try:
            _ocr_instance = RapidOCR()
        except Exception as e:
            print(f"[ERROR] OCR初始化失败: {e}")
            _ocr_instance = None
    return _ocr_instance


def extract_text_with_rapidocr(image_path, debug_folder=None):
    """
    使用RapidOCR提取文本
    Returns: OCR文本字符串，如果失败返回None
    """
    if not RAPIDOCR_AVAILABLE:
        return None

    try:
        # 处理PDF
        if Path(image_path).suffix.lower() == ".pdf":
            if not PDF_SUPPORT:
                return None
            project_root = os.path.dirname(os.path.abspath(__file__))
            poppler_path = os.path.join(project_root, "poppler-24.08.0", "Library", "bin")
            images = convert_from_path(image_path, first_page=1, last_page=1, dpi=200, poppler_path=poppler_path)

            if not images:
                return None

            # 保存临时图片
            import tempfile
            import numpy as np
            temp_img = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
            images[0].save(temp_img.name, 'JPEG', quality=95)
            image_to_process = temp_img.name
        else:
            image_to_process = image_path

        # RapidOCR识别
        ocr = get_ocr_instance()
        if not ocr:
            return None

        result, elapse = ocr(image_to_process)

        if not result:
            return ""

        # 提取文本
        texts = []
        ocr_details = []

        for line in result:
            # line格式: [[坐标], 文本, 置信度]
            box = line[0]
            text = line[1]
            confidence = line[2]

            texts.append(text)
            ocr_details.append({
                "text": text,
                "confidence": confidence,
                "box": box
            })

        full_text = "\n".join(texts)

        # 保存OCR结果用于debug
        if debug_folder:
            os.makedirs(debug_folder, exist_ok=True)
            filename = Path(image_path).stem
            debug_file = os.path.join(debug_folder, f"{filename}_ocr.json")

            debug_data = {
                "file": os.path.basename(image_path),
                "timestamp": datetime.now().isoformat(),
                "ocr_method": "RapidOCR",
                "text_count": len(texts),
                "full_text": full_text,
                "details": ocr_details
            }

            with open(debug_file, "w", encoding="utf-8") as f:
                json.dump(debug_data, f, ensure_ascii=False, indent=2)

        # 清理临时文件
        if Path(image_path).suffix.lower() == ".pdf":
            try:
                os.unlink(image_to_process)
            except:
                pass

        return full_text

    except Exception as e:
        print(f"   [ERROR] OCR失败: {e}")
        return None


def analyze_with_llm(ocr_text, image_path=None, debug_folder=None):
    """使用LLM分析OCR提取的文本"""
    prompt = f"""请分析以下OCR提取的发票文本，完成信息提取。

OCR识别文本：
{ocr_text}

分析任务：

1. 提取发票号码：
   - 找到发票号码（通常在顶部或中间位置）
   - 发票号码通常是20位数字
   - 如果没有发票号码，返回空字符串 ""

2. 提取金额（重要！）：
   - 仔细查看所有金额相关的文本
   - 找到总金额（价税合计、合计金额、支付金额、实收金额等）
   - 只要数字，去掉"¥"、"元"等符号，保留小数点
   - 如果看到多个金额，选择最大的总金额
   - 发票不太可能是0元，如果只看到0.00，请再次检查

3. 业务分类（重要！必须从以下三类中选一个）：

   【餐饮】- 所有与食品饮料相关的消费
   包括但不限于：
   - 明显的餐饮场所：餐厅、饭店、食堂、快餐店、外卖平台
   - 饮品店：咖啡店、奶茶店、茶饮店
   - 食品商家：水果店、蛋糕店、面包店、糕点店
   - 商品明细包含：食品、饮料、蔬菜、水果、糕点、餐费、餐饮服务等
   判断标准：只要商品明细中有任何食品、饮料、餐饮相关的词，就归为【餐饮】

   【交通】- 所有与交通出行相关的费用
   包括但不限于：
   - 打车/网约车：滴滴、出租车、网约车平台
   - 公共交通：地铁、公交、轮渡
   - 票务：火车票、飞机票、汽车票、船票
   - 快递/物流：顺丰、圆通、韵达等快递费、物流费、运费
   - 商品明细包含：运输服务、快递服务、物流服务、交通费等
   判断标准：商品明细中有运输、交通、快递、物流相关的词，就归为【交通】

   【住宿】- 所有与住宿相关的费用
   包括但不限于：
   - 酒店、宾馆、旅馆、旅店
   - 民宿、客栈
   - 商品明细包含：住宿费、房费、客房费等
   判断标准：商品明细中有住宿、客房相关的词，就归为【住宿】

   特殊情况：
   - 如果完全无法判断 → 优先归【餐饮】（最常见类型）
   - 绝对不要返回"其他"类型，必须从【餐饮】【交通】【住宿】三选一

4. 提取日期：
   - 优先提取开票日期
   - 转换为YYYYMMDD格式（如：20240115）

返回JSON（不要其他文字）：
{{
  "invoice_number": "发票号码",
  "amount": "金额数字",
  "type": "餐饮/交通/住宿",
  "date": "YYYYMMDD"
}}"""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }

    try:
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=120)
        if resp.status_code == 200:
            result = resp.json()
            content = result["choices"][0]["message"]["content"]

            # 保存LLM响应用于debug
            if debug_folder and image_path:
                filename = Path(image_path).stem
                debug_file = os.path.join(debug_folder, f"{filename}_llm.json")

                debug_data = {
                    "file": os.path.basename(image_path),
                    "timestamp": datetime.now().isoformat(),
                    "prompt": prompt,
                    "llm_response": content,
                    "model": MODEL_NAME
                }

                with open(debug_file, "w", encoding="utf-8") as f:
                    json.dump(debug_data, f, ensure_ascii=False, indent=2)

            # 提取JSON
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()

            invoice_info = json.loads(json_str)
            return invoice_info
        else:
            print(f"   [ERROR] API错误: {resp.status_code}")
            return None

    except Exception as e:
        print(f"   [ERROR] LLM分析失败: {e}")
        return None


def extract_invoice_info(image_path, debug_folder=None):
    """提取发票信息 - RapidOCR + LLM"""
    print(f"[处理] {os.path.basename(image_path)}")

    if not RAPIDOCR_AVAILABLE:
        print(f"   [ERROR] RapidOCR不可用")
        return None

    # 阶段1: OCR提取文本
    print("   [1/2] RapidOCR提取文本...")
    ocr_text = extract_text_with_rapidocr(image_path, debug_folder)

    if not ocr_text:
        print(f"   [ERROR] OCR提取失败")
        return None

    print(f"   [OK] OCR完成，提取 {len(ocr_text.split())} 行文本")

    # 阶段2: LLM分析
    print("   [2/2] LLM分析...")
    llm_result = analyze_with_llm(ocr_text, image_path, debug_folder)

    if not llm_result:
        print("   [ERROR] LLM分析失败")
        return None

    print(f"   [OK] {llm_result['amount']}元 | {llm_result['type']}")

    return llm_result


# 测试单个文件
if __name__ == "__main__":
    print("="*60)
    print("RapidOCR + LLM 测试")
    print("="*60)

    # 测试那个问题PDF
    test_file = r"C:\Users\17193\Desktop\发票整理工具\发票\output\无发票号\dzfp_26342000000164769331_国创决策智能技术研究所（常州）有限公司_20260212105809.pdf"

    if os.path.exists(test_file):
        debug_folder = r"C:\Users\17193\Desktop\发票整理工具\ocr_debug"
        os.makedirs(debug_folder, exist_ok=True)

        print(f"\n测试文件: {os.path.basename(test_file)}")
        print(f"Debug输出: {debug_folder}")
        print("-"*60)

        result = extract_invoice_info(test_file, debug_folder)

        if result:
            print("\n识别结果:")
            print(f"  发票号码: {result.get('invoice_number', 'N/A')}")
            print(f"  金额: {result.get('amount', 'N/A')} 元")
            print(f"  类型: {result.get('type', 'N/A')}")
            print(f"  日期: {result.get('date', 'N/A')}")

            print(f"\nDebug文件已保存:")
            print(f"  - OCR结果: {debug_folder}/{{filename}}_ocr.json")
            print(f"  - LLM响应: {debug_folder}/{{filename}}_llm.json")
    else:
        print(f"文件不存在: {test_file}")

    print("="*60)
