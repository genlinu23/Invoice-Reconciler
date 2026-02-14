"""
发票信息提取模块
使用 OCR + LLM 提取发票信息和计算金额
"""
import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# 导入PaddleOCR
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except (ImportError, Exception):
    PADDLEOCR_AVAILABLE = False

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

# OCR实例（单例模式）
_ocr_instance = None


def get_ocr_instance():
    """获取OCR实例（单例模式）"""
    global _ocr_instance
    if _ocr_instance is None:
        if not PADDLEOCR_AVAILABLE:
            return None
        try:
            _ocr_instance = PaddleOCR(
                use_angle_cls=True,
                lang='ch',
                use_gpu=False,
                show_log=False,
                det_db_thresh=0.3,
                det_db_box_thresh=0.5,
                det_db_unclip_ratio=1.6,
                rec_batch_num=6,
                max_text_length=25,
            )
        except Exception as e:
            print(f"[ERROR] OCR初始化失败: {e}")
            _ocr_instance = None
    return _ocr_instance


def extract_text_from_pdf(pdf_path):
    """使用pdfplumber提取PDF文本"""
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except:
        return ""


def extract_text_with_ocr(image_path):
    """
    提取文件文字（OCR + PDF文本提取）
    """
    texts = []
    full_text = ""
    pdf_text = ""
    structured = []

    # 1. 尝试直接提取PDF文本
    if Path(image_path).suffix.lower() == ".pdf":
        pdf_text = extract_text_from_pdf(image_path)
        if pdf_text:
            texts = pdf_text.split('\n')

    # 2. 如果OCR可用，尝试OCR
    if PADDLEOCR_AVAILABLE:
        try:
            image_to_process = None
            
            if Path(image_path).suffix.lower() == ".pdf":
                if PDF_SUPPORT:
                    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    poppler_path = os.path.join(project_root, "poppler-24.08.0", "Library", "bin")
                    images = convert_from_path(image_path, first_page=1, last_page=1, dpi=150, poppler_path=poppler_path)
                    if images:
                        import numpy as np
                        image_to_process = np.array(images[0])
            else:
                image_to_process = image_path

            if image_to_process is not None:
                ocr = get_ocr_instance()
                if ocr:
                    result = ocr.ocr(image_to_process, cls=True)
                    if result and result[0]:
                        # OCR成功，处理结果
                        ocr_texts = []
                        for line in result[0]:
                            text = line[1][0]
                            confidence = line[1][1]
                            ocr_texts.append(text)
                            structured.append({
                                "text": text,
                                "confidence": round(confidence, 4),
                                "bbox": line[0]
                            })
                        full_text = "\n".join(ocr_texts)
                        
                        # 如果PDF提取失败（为空），则使用OCR的文本列表
                        if not texts:
                            texts = ocr_texts
        except Exception as e:
            print(f"[WARN] OCR处理异常: {e}")

    # 3. 汇总结果
    if not full_text and not pdf_text:
        return None

    return {
        "texts": texts,         
        "full_text": full_text, 
        "pdf_text": pdf_text,
        "structured": structured
    }


def analyze_with_llm(ocr_text, pdf_text=""):
    """
    使用LLM分析OCR提取的文本

    Args:
        ocr_text: OCR提取的文本
        pdf_text: PDF直接提取的文本（可选）

    Returns:
        dict: {
            "amount": "金额",
            "type": "餐饮/交通/住宿/其他",
            "date": "YYYYMMDD"
        }
    """
    prompt = f"""请分析以下发票文本，完成信息提取。

OCR识别文本（视觉识别）：
{ocr_text}

PDF提取文本（直接提取）：
{pdf_text}

分析任务：

1. 提取金额：
   - 找到总金额（价税合计、支付金额等）
   - 只要数字，去掉"¥"、"元"等符号
   - 保留小数点

2. 业务分类：
   【餐饮】餐厅、饭店、食堂、外卖、咖啡店、奶茶店等餐饮场所
   【交通】打车、出租车、火车、飞机、租车、停车等交通费用
   【住宿】酒店、宾馆、旅馆、民宿等住宿场所
   【其他】不符合以上类别的，或商贸公司、批发商等

3. 提取日期：
   - 优先提取开票日期
   - 转换为YYYYMMDD格式（如：20240115）

返回JSON（不要其他文字）：
{{
  "amount": "金额数字",
  "type": "餐饮/交通/住宿/其他",
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
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            result = resp.json()
            content = result["choices"][0]["message"]["content"]

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
            print(f"[ERROR] LLM API错误: {resp.status_code}")
            return None

    except Exception as e:
        print(f"[ERROR] LLM分析失败: {e}")
        return None


def extract_invoice_info(image_path):
    """
    发票信息提取主函数

    Args:
        image_path: 图片路径

    Returns:
        dict: 提取的发票信息 {"amount": "金额", "type": "类型", "date": "日期"}
    """
    print(f"[处理] {os.path.basename(image_path)}")

    if not PADDLEOCR_AVAILABLE:
        print(f"   [WARN] OCR模块未加载，尝试使用PDF直接提取...")
        # 继续执行，因为extract_text_with_ocr现在可以处理这种情况

    # 阶段1: OCR提取文本
    print("   [1/2] 文本提取...")
    ocr_result = extract_text_with_ocr(image_path)

    if not ocr_result:
        print(f"   [ERROR] 提取失败 (可能是空白文件或格式不支持)")
        return None

    print(f"   [OK] 提取完成，共 {len(ocr_result['texts'])} 行")

    # 阶段2: LLM分析
    print("   [2/2] LLM分析...")
    pdf_text = ocr_result.get("pdf_text", "")
    if pdf_text:
        print(f"   [INFO] PDF文本提取成功 ({len(pdf_text)} 字符)")
        
    llm_result = analyze_with_llm(ocr_result["full_text"], pdf_text)

    if not llm_result:
        print("   [ERROR] LLM分析失败")
        return None

    print(f"   [OK] 提取完成: {llm_result['amount']}元 | {llm_result['type']}")

    return llm_result


# 兼容旧接口
def analyze_invoice(image_path):
    """兼容旧版接口"""
    return extract_invoice_info(image_path)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python invoice_extractor.py <图片路径>")
        sys.exit(1)

    test_image = sys.argv[1]

    if not os.path.exists(test_image):
        print(f"[ERROR] 文件不存在: {test_image}")
        sys.exit(1)

    print("="*60)
    print("发票信息提取测试")
    print("="*60)

    result = extract_invoice_info(test_image)

    if result:
        print("\n" + "="*60)
        print("提取结果:")
        print("="*60)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("\n[ERROR] 提取失败")
