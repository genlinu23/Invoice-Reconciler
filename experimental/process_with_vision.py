"""
直接使用视觉模型处理发票（绕过OCR）
临时解决方案，用于处理发票文件夹
"""
import os
import sys
import json
import base64
import requests
from pathlib import Path
from shutil import copy2
from dotenv import load_dotenv
from io import BytesIO

# PDF转图片支持
try:
    from pdf2image import convert_from_path
    from PIL import Image
    PDF_SUPPORT = True
except:
    PDF_SUPPORT = False

# 加载环境变量
load_dotenv()
API_URL = os.getenv("API_BASE_URL", "http://45.120.102.120:10021/v1/chat/completions")
API_KEY = os.getenv("API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen3-VL-235B-A22B-Instruct-FP8")


def extract_invoice_with_vision(image_path):
    """使用视觉模型直接提取发票信息"""
    print(f"[处理] {os.path.basename(image_path)}")

    try:
        # 处理PDF：转换为图片
        if Path(image_path).suffix.lower() == ".pdf":
            if not PDF_SUPPORT:
                print("   [ERROR] 未安装pdf2image")
                return None

            # 转换PDF第一页为图片
            project_root = os.path.dirname(os.path.abspath(__file__))
            poppler_path = os.path.join(project_root, "poppler-24.08.0", "Library", "bin")
            images = convert_from_path(image_path, first_page=1, last_page=1, dpi=150, poppler_path=poppler_path)

            if not images:
                print("   [ERROR] PDF转换失败")
                return None

            # 将PIL图片转换为字节
            img_buffer = BytesIO()
            images[0].save(img_buffer, format='JPEG', quality=95)
            img_data = img_buffer.getvalue()
            img_b64 = base64.b64encode(img_data).decode()
        else:
            # 直接读取图片
            with open(image_path, "rb") as f:
                img_data = f.read()
                img_b64 = base64.b64encode(img_data).decode()

        # 构建prompt
        prompt = """请分析这张发票图片，提取以下信息：

1. 提取发票号码：
   - 找到发票号码（通常在发票顶部或中间位置）
   - 如果没有发票号码，返回空字符串 ""

2. 提取金额：
   - 找到总金额（价税合计、支付金额等）
   - 只要数字，去掉"¥"、"元"等符号
   - 保留小数点
   - 如果是0元或没有金额，请仔细查看是否有实际金额

3. 业务分类：
   【餐饮】餐厅、饭店、食堂、外卖、咖啡店、奶茶店等餐饮场所
   【交通】打车、出租车、火车、飞机、租车、停车等交通费用
   【住宿】酒店、宾馆、旅馆、民宿等住宿场所
   【其他】不符合以上类别的，或商贸公司、批发商等

4. 提取日期：
   - 优先提取开票日期
   - 转换为YYYYMMDD格式（如：20240115）

返回JSON（不要其他文字）：
{
  "invoice_number": "发票号码",
  "amount": "金额数字",
  "type": "餐饮/交通/住宿/其他",
  "date": "YYYYMMDD"
}"""

        # 调用API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
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
            print(f"   [OK] {invoice_info['amount']}元 | {invoice_info['type']}")
            return invoice_info
        else:
            print(f"   [ERROR] API错误: {resp.status_code}")
            return None

    except Exception as e:
        print(f"   [ERROR] 处理失败: {e}")
        return None


def process_folder(input_folder, output_folder=None):
    """处理发票文件夹"""
    # 设置输出文件夹
    if not output_folder:
        output_folder = os.path.join(input_folder, "output")

    os.makedirs(output_folder, exist_ok=True)

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
        "total_amount": 0.0,
        "by_type": {}
    }

    # 处理每个文件
    for idx, file_path in enumerate(image_files, 1):
        print(f"\n[{idx}/{len(image_files)}]")

        try:
            # 提取发票信息
            invoice_info = extract_invoice_with_vision(file_path)

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
                stats["failed"] += 1
                continue

            # 检查金额是否为0
            try:
                amount_float = float(amount)
                if amount_float == 0:
                    print(f"   [WARNING] 金额为0，请检查识别是否正确")
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

            # 处理重名
            new_path = os.path.join(output_folder, new_filename)
            counter = 1
            while os.path.exists(new_path):
                if date:
                    new_filename = f"{amount}_{inv_type}_{date}_{counter}{file_ext}"
                else:
                    new_filename = f"{amount}_{inv_type}_{counter}{file_ext}"
                new_path = os.path.join(output_folder, new_filename)
                counter += 1

            # 复制文件
            copy2(file_path, new_path)

            # 记录已处理的发票号码
            if invoice_number:
                processed_invoices[invoice_number] = new_filename

            print(f"   [SAVED] -> {new_filename}")
            if invoice_number:
                print(f"   发票号: {invoice_number}")
            stats["success"] += 1

        except Exception as e:
            print(f"   [ERROR] {e}")
            stats["failed"] += 1

    return stats


def print_statistics(stats):
    """打印统计信息"""
    print("\n" + "="*60)
    print("处理统计")
    print("="*60)
    print(f"总文件数: {stats['total']}")
    print(f"成功: {stats['success']}")
    print(f"失败: {stats['failed']}")
    print(f"总金额: {stats['total_amount']:.2f} 元")

    print("\n按类型统计:")
    print("-"*60)
    for inv_type, data in stats["by_type"].items():
        print(f"  {inv_type:6s}: {data['count']:3d} 个 | {data['amount']:10.2f} 元")
    print("="*60)


def main():
    print("="*60)
    print("发票整理工具 - 视觉模型版")
    print("="*60)

    # 获取输入文件夹
    if len(sys.argv) > 1:
        input_folder = sys.argv[1]
    else:
        print("[ERROR] 请指定发票文件夹路径")
        print("用法: python process_with_vision.py <发票文件夹路径>")
        return

    # 检查文件夹
    if not os.path.exists(input_folder):
        print(f"[ERROR] 文件夹不存在: {input_folder}")
        return

    # 获取输出文件夹
    output_folder = sys.argv[2] if len(sys.argv) > 2 else None

    # 处理文件夹
    stats = process_folder(input_folder, output_folder)

    if stats:
        # 打印统计
        print_statistics(stats)

        # 保存统计到JSON
        output_dir = output_folder or os.path.join(input_folder, "output")
        stats_file = os.path.join(output_dir, "statistics.json")
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"\n统计信息已保存到: {stats_file}")


if __name__ == "__main__":
    main()
