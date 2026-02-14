"""
发票整理工具 - OCR + LLM 文本分析版
先OCR提取文本，再用LLM分析
"""
import os
import sys
import json
import requests
from pathlib import Path
from shutil import copy2
from dotenv import load_dotenv

# 导入PaddleOCR
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except (ImportError, Exception):
    PADDLEOCR_AVAILABLE = False
    print("[WARNING] PaddleOCR未安装，将使用视觉模型")

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
    """获取OCR实例"""
    global _ocr_instance
    if _ocr_instance is None and PADDLEOCR_AVAILABLE:
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


def extract_text_with_ocr(image_path):
    """使用PaddleOCR提取文字"""
    if not PADDLEOCR_AVAILABLE:
        return None

    try:
        # 处理PDF
        if Path(image_path).suffix.lower() == ".pdf":
            if not PDF_SUPPORT:
                return None
            project_root = os.path.dirname(os.path.abspath(__file__))
            poppler_path = os.path.join(project_root, "poppler-24.08.0", "Library", "bin")
            images = convert_from_path(image_path, first_page=1, last_page=1, dpi=150, poppler_path=poppler_path)
            if images:
                import numpy as np
                image_to_process = np.array(images[0])
            else:
                return None
        else:
            image_to_process = image_path

        # OCR识别
        ocr = get_ocr_instance()
        if not ocr:
            return None

        result = ocr.ocr(image_to_process, cls=True)

        if not result or not result[0]:
            return ""

        # 提取文本
        texts = []
        for line in result[0]:
            text = line[1][0]
            texts.append(text)

        # 拼接完整文本
        full_text = "\n".join(texts)
        return full_text

    except Exception as e:
        print(f"   [ERROR] OCR失败: {e}")
        return None


def analyze_with_llm(ocr_text):
    """使用LLM分析OCR提取的文本"""
    prompt = f"""请分析以下OCR提取的发票文本，完成信息提取。

OCR识别文本：
{ocr_text}

分析任务：

1. 提取发票号码：
   - 找到发票号码（通常在顶部或中间位置）
   - 如果没有发票号码，返回空字符串 ""

2. 提取金额：
   - 仔细查看所有金额相关的文本
   - 找到总金额（价税合计、合计金额、支付金额、实收金额等）
   - 只要数字，去掉"¥"、"元"等符号，保留小数点
   - 如果看到多个金额，选择最大的总金额
   - 发票不太可能是0元，如果只看到0.00，请再次检查

3. 业务分类（重要！请仔细判断）：
   根据商家名称、商品明细、服务内容等综合判断：

   【餐饮】包括但不限于：
   - 餐厅、饭店、食堂、快餐店
   - 外卖、咖啡店、奶茶店、茶饮店
   - 水果店、蛋糕店、面包店
   - 小吃店、烧烤店、火锅店
   - 任何与食品、饮料相关的消费

   【交通】包括但不限于：
   - 打车、出租车、网约车
   - 火车票、飞机票、汽车票
   - 租车、停车费
   - 地铁、公交

   【住宿】包括但不限于：
   - 酒店、宾馆、旅馆
   - 民宿、客栈

   【其他】：
   - 不符合以上任何类别的
   - 如：办公用品、技术服务、咨询服务等

4. 提取日期：
   - 优先提取开票日期
   - 转换为YYYYMMDD格式（如：20240115）

返回JSON（不要其他文字）：
{{
  "invoice_number": "发票号码",
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
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=120)
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
            print(f"   [ERROR] API错误: {resp.status_code}")
            return None

    except Exception as e:
        print(f"   [ERROR] LLM分析失败: {e}")
        return None


def extract_invoice_info(image_path):
    """提取发票信息 - OCR + LLM"""
    print(f"[处理] {os.path.basename(image_path)}")

    if not PADDLEOCR_AVAILABLE:
        print(f"   [ERROR] OCR不可用")
        return None

    # 阶段1: OCR提取文本
    print("   [1/2] OCR提取文本...")
    ocr_text = extract_text_with_ocr(image_path)

    if not ocr_text:
        print(f"   [ERROR] OCR提取失败")
        return None

    print(f"   [OK] OCR完成，共 {len(ocr_text.split())} 行")

    # 阶段2: LLM分析
    print("   [2/2] LLM分析...")
    llm_result = analyze_with_llm(ocr_text)

    if not llm_result:
        print("   [ERROR] LLM分析失败")
        return None

    print(f"   [OK] {llm_result['amount']}元 | {llm_result['type']}")

    return llm_result


def process_folder(input_folder, output_folder=None):
    """处理发票文件夹 - 按类型分类"""
    if not output_folder:
        output_folder = os.path.join(input_folder, "output")

    os.makedirs(output_folder, exist_ok=True)

    # 创建分类文件夹
    categories = ["餐饮", "交通", "住宿", "其他"]
    category_folders = {}
    for category in categories:
        folder_path = os.path.join(output_folder, category)
        os.makedirs(folder_path, exist_ok=True)
        category_folders[category] = folder_path

    # 用于跟踪已处理的发票号码
    processed_invoices = {}

    # 支持的格式
    supported_formats = [".jpg", ".jpeg", ".png", ".pdf"]

    # 获取所有图片文件
    image_files = []
    for root, dirs, files in os.walk(input_folder):
        if "output" in dirs:
            dirs.remove("output")
        for file in files:
            if Path(file).suffix.lower() in supported_formats:
                image_files.append(os.path.join(root, file))

    if not image_files:
        print("[ERROR] 未找到任何图片文件")
        return None

    print(f"\n找到 {len(image_files)} 个文件")
    print("="*60)

    # 统计信息
    stats = {
        "total": len(image_files),
        "success": 0,
        "failed": 0,
        "duplicate": 0,
        "total_amount": 0.0,
        "by_type": {}
    }

    # 处理每个文件
    for idx, file_path in enumerate(image_files, 1):
        print(f"\n[{idx}/{len(image_files)}]")

        try:
            # 提取发票信息
            invoice_info = extract_invoice_info(file_path)

            if not invoice_info:
                stats["failed"] += 1
                continue

            # 提取信息
            invoice_number = invoice_info.get("invoice_number", "")
            amount = invoice_info.get("amount", "0")
            inv_type = invoice_info.get("type", "其他")
            date = invoice_info.get("date", "")

            # 检查发票号码重复
            if invoice_number and invoice_number in processed_invoices:
                print(f"   [SKIP] 发票号码重复: {invoice_number}")
                print(f"   已存在文件: {processed_invoices[invoice_number]}")
                stats["duplicate"] += 1
                stats["failed"] += 1
                continue

            # 检查金额
            try:
                amount_float = float(amount)
                if amount_float == 0:
                    print(f"   [WARNING] 金额为0，请人工检查")
            except:
                amount_float = 0.0

            # 统计金额
            stats["total_amount"] += amount_float

            # 统计类型
            if inv_type not in stats["by_type"]:
                stats["by_type"][inv_type] = {"count": 0, "amount": 0.0}
            stats["by_type"][inv_type]["count"] += 1
            stats["by_type"][inv_type]["amount"] += amount_float

            # 生成新文件名
            file_ext = Path(file_path).suffix
            if date:
                new_filename = f"{amount}_{inv_type}_{date}{file_ext}"
            else:
                new_filename = f"{amount}_{inv_type}{file_ext}"

            # 确定目标文件夹
            target_folder = category_folders.get(inv_type, category_folders["其他"])

            # 处理重名
            new_path = os.path.join(target_folder, new_filename)
            counter = 1
            while os.path.exists(new_path):
                if date:
                    new_filename = f"{amount}_{inv_type}_{date}_{counter}{file_ext}"
                else:
                    new_filename = f"{amount}_{inv_type}_{counter}{file_ext}"
                new_path = os.path.join(target_folder, new_filename)
                counter += 1

            # 复制文件到对应分类文件夹
            copy2(file_path, new_path)

            # 记录已处理的发票号码
            if invoice_number:
                processed_invoices[invoice_number] = new_filename

            print(f"   [SAVED] -> {inv_type}/{new_filename}")
            if invoice_number:
                print(f"   发票号: {invoice_number}")
            stats["success"] += 1

        except Exception as e:
            print(f"   [ERROR] {e}")
            stats["failed"] += 1

    return stats, output_folder


def print_statistics(stats):
    """打印统计信息"""
    print("\n" + "="*60)
    print("处理统计")
    print("="*60)
    print(f"总文件数: {stats['total']}")
    print(f"成功: {stats['success']}")
    print(f"重复: {stats.get('duplicate', 0)}")
    print(f"失败: {stats['failed'] - stats.get('duplicate', 0)}")
    print(f"总金额: {stats['total_amount']:.2f} 元")

    print("\n按类型统计:")
    print("-"*60)
    for inv_type, data in stats["by_type"].items():
        print(f"  {inv_type:6s}: {data['count']:3d} 个 | {data['amount']:10.2f} 元")
    print("="*60)


def main():
    """主函数"""
    print("="*60)
    print("发票整理工具 - OCR+LLM版")
    print("先OCR提取文字，再LLM分析")
    print("自动分类到：餐饮/交通/住宿/其他文件夹")
    print("="*60)

    if len(sys.argv) > 1:
        input_folder = sys.argv[1]
    else:
        print("[ERROR] 请指定发票文件夹路径")
        print("用法: python process_with_ocr_llm.py <发票文件夹路径>")
        return

    if not os.path.exists(input_folder):
        print(f"[ERROR] 文件夹不存在: {input_folder}")
        return

    output_folder = sys.argv[2] if len(sys.argv) > 2 else None

    # 处理文件夹
    result = process_folder(input_folder, output_folder)

    if result:
        stats, output_dir = result

        # 打印统计
        print_statistics(stats)

        # 保存统计到JSON
        stats_file = os.path.join(output_dir, "statistics.json")
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"\n统计信息已保存到: {stats_file}")

        # 显示文件夹结构
        print("\n分类文件夹:")
        print("-"*60)
        for category in ["餐饮", "交通", "住宿", "其他"]:
            folder_path = os.path.join(output_dir, category)
            file_count = len([f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))])
            print(f"  {category}: {file_count} 个文件 -> {folder_path}")


if __name__ == "__main__":
    main()
