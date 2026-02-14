"""
发票整理工具 - LLM OCR版本
使用LLM的视觉能力同时做OCR和分析，保存详细debug信息
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
from io import BytesIO

# 设置UTF-8输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# PDF支持
try:
    from pdf2image import convert_from_path
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# 加载环境变量
load_dotenv()
API_URL = os.getenv("API_BASE_URL", "http://45.120.102.120:10021/v1/chat/completions")
API_KEY = os.getenv("API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen3-VL-235B-A22B-Instruct-FP8")


def extract_invoice_with_llm_ocr(image_path, debug_folder=None):
    """
    使用LLM同时做OCR和信息提取
    先让LLM提取所有文本(OCR)，再分析信息
    """
    print(f"[处理] {os.path.basename(image_path)}")

    try:
        # 转换图片
        if Path(image_path).suffix.lower() == ".pdf":
            if not PDF_SUPPORT:
                print("   [ERROR] PDF支持不可用")
                return None

            project_root = os.path.dirname(os.path.abspath(__file__))
            poppler_path = os.path.join(project_root, "poppler-24.08.0", "Library", "bin")
            images = convert_from_path(image_path, first_page=1, last_page=1, dpi=300, poppler_path=poppler_path)  # 提高到300 DPI

            if not images:
                print("   [ERROR] PDF转换失败")
                return None

            img_buffer = BytesIO()
            images[0].save(img_buffer, format='JPEG', quality=98)  # 提高质量到98
            img_data = img_buffer.getvalue()
            img_b64 = base64.b64encode(img_data).decode()
        else:
            with open(image_path, "rb") as f:
                img_data = f.read()
                img_b64 = base64.b64encode(img_data).decode()

        # 步骤1: 先让LLM提取所有文本(OCR)
        print("   [1/2] LLM提取文本(OCR)...")
        ocr_prompt = """请仔细查看这张发票图片，提取所有可见的文本内容。

要求：
1. 按从上到下、从左到右的顺序提取
2. 保持原始格式和换行
3. 包括所有数字、日期、金额
4. 特别注意右上角的发票号码
5. 提取所有小字和数字

直接返回提取的文本，不要添加任何解释。"""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": ocr_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                ]
            }
        ]

        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": 0.1
        }

        resp = requests.post(API_URL, headers=headers, json=payload, timeout=120)

        if resp.status_code != 200:
            print(f"   [ERROR] OCR API错误: {resp.status_code}")
            return None

        ocr_result = resp.json()
        ocr_text = ocr_result["choices"][0]["message"]["content"]

        print(f"   [OK] OCR完成，提取了 {len(ocr_text)} 字符")

        # 保存OCR结果
        if debug_folder:
            os.makedirs(debug_folder, exist_ok=True)
            filename = Path(image_path).stem
            ocr_debug_file = os.path.join(debug_folder, f"{filename}_ocr.json")

            ocr_debug_data = {
                "file": os.path.basename(image_path),
                "timestamp": datetime.now().isoformat(),
                "ocr_method": "LLM_OCR",
                "model": MODEL_NAME,
                "ocr_text": ocr_text,
                "text_length": len(ocr_text),
                "prompt": ocr_prompt
            }

            with open(ocr_debug_file, "w", encoding="utf-8") as f:
                json.dump(ocr_debug_data, f, ensure_ascii=False, indent=2)

        # 步骤2: 使用OCR文本进行信息提取
        print("   [2/2] LLM分析信息...")
        analysis_prompt = f"""请分析以下OCR提取的发票文本，完成信息提取。

OCR识别文本：
{ocr_text}

分析任务：

1. 提取发票号码（非常重要！）：
   - 发票号码通常是20位数字
   - 通常在发票右上角，标注为"发票号码"或"No"
   - 仔细查找所有20位数字
   - 如果没有，返回空字符串 ""

2. 提取金额（重要！）：
   - 找到"价税合计"、"合计金额"、"支付金额"等字段
   - 只要数字，去掉"¥"、"元"等符号
   - 如果看到多个金额，选择最大的总金额
   - 发票不太可能是0元

3. 业务分类（必须从以下三类中选一个）：
   【餐饮】- 食品、饮料、餐饮服务、水果、糕点等
   【交通】- 打车、快递、物流、运输服务、车票等
   【住宿】- 酒店、宾馆、住宿费等

   判断标准：查看商品明细或服务名称
   如果无法判断 → 默认【餐饮】

4. 提取日期：
   - 优先提取开票日期
   - 转换为YYYYMMDD格式

返回JSON（不要其他文字）：
{{
  "invoice_number": "发票号码",
  "amount": "金额数字",
  "type": "餐饮/交通/住宿",
  "date": "YYYYMMDD"
}}"""

        payload2 = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": analysis_prompt}],
            "temperature": 0.1
        }

        resp2 = requests.post(API_URL, headers=headers, json=payload2, timeout=120)

        if resp2.status_code != 200:
            print(f"   [ERROR] 分析API错误: {resp2.status_code}")
            return None

        analysis_result = resp2.json()
        content = analysis_result["choices"][0]["message"]["content"]

        # 保存分析结果
        if debug_folder:
            analysis_debug_file = os.path.join(debug_folder, f"{filename}_analysis.json")

            analysis_debug_data = {
                "file": os.path.basename(image_path),
                "timestamp": datetime.now().isoformat(),
                "analysis_method": "LLM_Text_Analysis",
                "model": MODEL_NAME,
                "prompt": analysis_prompt,
                "llm_response": content
            }

            with open(analysis_debug_file, "w", encoding="utf-8") as f:
                json.dump(analysis_debug_data, f, ensure_ascii=False, indent=2)

        # 提取JSON
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content.strip()

        invoice_info = json.loads(json_str)
        print(f"   [OK] {invoice_info.get('amount', '?')}元 | {invoice_info.get('type', '?')}")

        return invoice_info

    except Exception as e:
        print(f"   [ERROR] 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return None


# 测试
if __name__ == "__main__":
    print("="*60)
    print("LLM OCR + 分析测试（高质量版本）")
    print("="*60)

    # 测试问题PDF
    test_file = r"C:\Users\17193\Desktop\发票整理工具\发票\output\无发票号\dzfp_26342000000164769331_国创决策智能技术研究所（常州）有限公司_20260212105809.pdf"

    if os.path.exists(test_file):
        debug_folder = r"C:\Users\17193\Desktop\发票整理工具\ocr_debug"
        os.makedirs(debug_folder, exist_ok=True)

        print(f"\n测试文件: {os.path.basename(test_file)}")
        print(f"Debug输出: {debug_folder}")
        print(f"改进: DPI=300, 质量=98%")
        print("-"*60)

        result = extract_invoice_with_llm_ocr(test_file, debug_folder)

        if result:
            print("\n" + "="*60)
            print("识别结果:")
            print("="*60)
            print(f"  发票号码: {result.get('invoice_number', 'N/A')}")
            print(f"  金额: {result.get('amount', 'N/A')} 元")
            print(f"  类型: {result.get('type', 'N/A')}")
            print(f"  日期: {result.get('date', 'N/A')}")

            print("\n期望结果（根据图片）:")
            print("  发票号码: 26342000000164769331")
            print("  金额: 38.90 元")
            print("  类型: 餐饮")
            print("  日期: 20260118")

            print(f"\nDebug文件:")
            filename = Path(test_file).stem
            print(f"  1. OCR提取: {debug_folder}/{filename}_ocr.json")
            print(f"  2. LLM分析: {debug_folder}/{filename}_analysis.json")
            print("\n可以查看这些JSON文件了解LLM的完整输出")
    else:
        print(f"文件不存在: {test_file}")

    print("="*60)
