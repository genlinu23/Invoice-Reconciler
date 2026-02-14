"""
发票整理工具 - 按类型分类到不同文件夹
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

        # 构建prompt - 强调商品明细判断，消除"其他"类目
        prompt = """请分析这张发票图片，提取以下信息：

1. 提取发票号码：
   - 找到发票号码（通常在发票顶部或中间位置）
   - 如果没有发票号码，返回空字符串 ""

2. 提取金额（重要！）：
   - 仔细查看整张发票的所有区域
   - 找到总金额（价税合计、合计金额、支付金额、实收金额等）
   - 只要数字，去掉"¥"、"元"等符号，保留小数点
   - 如果看到多个金额，选择最大的总金额
   - 发票几乎不可能是0元，如果只看到0.00，请再次仔细检查其他区域

3. 业务分类（重要！必须从以下三类中选一个）：

   判断优先级：
   第1步：查看发票上的"货物或应税劳务、服务名称"、"项目名称"、"商品明细"等栏位
   第2步：根据商品/服务内容判断类型
   第3步：如果看不清商品明细，再看商家名称

   分类规则（只能选以下三类之一）：

   【餐饮】- 所有与食品饮料相关的消费
   包括但不限于：
   - 明显的餐饮场所：餐厅、饭店、食堂、快餐店、外卖平台
   - 饮品店：咖啡店、奶茶店、茶饮店、果汁店
   - 食品商家：水果店、蛋糕店、面包店、糕点店、小吃店
   - 商品明细包含：食品、饮料、蔬菜、水果、糕点、面包、饮品、餐费、外卖等
   - 超市/便利店购买食品饮料的发票
   - 烧烤、火锅、自助餐等餐饮
   判断标准：只要商品明细中有任何食品、饮料、餐饮相关的词，就归为【餐饮】

   【交通】- 所有与交通出行相关的费用
   包括但不限于：
   - 打车/网约车：滴滴、出租车、网约车平台
   - 公共交通：地铁、公交、轮渡
   - 票务：火车票、飞机票、汽车票、船票
   - 其他交通：租车、停车费、过路费、加油费
   - 快递/物流：顺丰、圆通、韵达等快递费、物流费、运费
   - 商品明细包含：运输服务、快递服务、物流服务、交通费、车费、票费等
   判断标准：商品明细中有运输、交通、快递、物流相关的词，就归为【交通】

   【住宿】- 所有与住宿相关的费用
   包括但不限于：
   - 酒店、宾馆、旅馆、旅店
   - 民宿、客栈、青年旅社
   - 商品明细包含：住宿费、房费、客房费等
   判断标准：商品明细中有住宿、客房相关的词，就归为【住宿】

   特殊情况处理：
   - 如果是商贸公司、批发商开的发票，但商品是食品饮料 → 归【餐饮】
   - 如果是技术公司、咨询公司开的发票，但看不到明确服务内容 → 优先归【餐饮】（可能是员工餐费）
   - 如果完全无法判断 → 优先归【餐饮】（最常见的报销类型）
   - 绝对不要返回"其他"类型，必须从【餐饮】【交通】【住宿】三选一

4. 提取日期：
   - 优先提取开票日期
   - 转换为YYYYMMDD格式（如：20240115）

返回JSON（不要其他文字，type字段只能是"餐饮"、"交通"或"住宿"之一）：
{
  "invoice_number": "发票号码",
  "amount": "金额数字",
  "type": "餐饮/交通/住宿",
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
    """处理发票文件夹 - 按类型分类"""
    # 设置输出文件夹
    if not output_folder:
        output_folder = os.path.join(input_folder, "output")

    os.makedirs(output_folder, exist_ok=True)

    # 创建分类文件夹（只有三类）
    categories = ["餐饮", "交通", "住宿"]
    category_folders = {}
    for category in categories:
        folder_path = os.path.join(output_folder, category)
        os.makedirs(folder_path, exist_ok=True)
        category_folders[category] = folder_path

    # 创建"无发票号"文件夹，用于存放没有发票号码的文件
    no_invoice_number_folder = os.path.join(output_folder, "无发票号")
    os.makedirs(no_invoice_number_folder, exist_ok=True)

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
        "no_invoice_number": 0,
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

            # 检查是否有发票号码（必须有发票号码才算正式发票）
            if not invoice_number or invoice_number.strip() == "":
                print(f"   [FILTER] 无发票号码，移动到'无发票号'文件夹")

                # 生成文件名
                file_ext = Path(file_path).suffix
                original_filename = os.path.basename(file_path)
                new_path = os.path.join(no_invoice_number_folder, original_filename)

                # 处理重名
                counter = 1
                while os.path.exists(new_path):
                    name_without_ext = Path(original_filename).stem
                    new_path = os.path.join(no_invoice_number_folder, f"{name_without_ext}_{counter}{file_ext}")
                    counter += 1

                # 复制文件
                copy2(file_path, new_path)
                stats["no_invoice_number"] += 1
                stats["failed"] += 1
                print(f"   [SAVED] -> 无发票号/{os.path.basename(new_path)}")
                continue

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

            # 确定目标文件夹（如果类型不在列表中，默认为餐饮）
            if inv_type not in category_folders:
                print(f"   [WARNING] 未知类型'{inv_type}'，归类为餐饮")
                inv_type = "餐饮"
            target_folder = category_folders[inv_type]

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
    print(f"无发票号: {stats.get('no_invoice_number', 0)}")
    print(f"失败: {stats['failed'] - stats.get('duplicate', 0) - stats.get('no_invoice_number', 0)}")
    print(f"总金额: {stats['total_amount']:.2f} 元")

    print("\n按类型统计:")
    print("-"*60)
    for inv_type, data in stats["by_type"].items():
        print(f"  {inv_type:6s}: {data['count']:3d} 个 | {data['amount']:10.2f} 元")
    print("="*60)


def main():
    """主函数"""
    print("="*60)
    print("发票整理工具 - 分类版")
    print("自动分类到：餐饮/交通/住宿文件夹")
    print("="*60)

    # 获取输入文件夹
    if len(sys.argv) > 1:
        input_folder = sys.argv[1]
    else:
        print("[ERROR] 请指定发票文件夹路径")
        print("用法: python process_with_categories.py <发票文件夹路径>")
        return

    # 检查文件夹
    if not os.path.exists(input_folder):
        print(f"[ERROR] 文件夹不存在: {input_folder}")
        return

    # 获取输出文件夹
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
        for category in ["餐饮", "交通", "住宿"]:
            folder_path = os.path.join(output_dir, category)
            if os.path.exists(folder_path):
                file_count = len([f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))])
                print(f"  {category}: {file_count} 个文件 -> {folder_path}")

        # 显示无发票号文件夹
        no_invoice_folder = os.path.join(output_dir, "无发票号")
        if os.path.exists(no_invoice_folder):
            file_count = len([f for f in os.listdir(no_invoice_folder) if os.path.isfile(os.path.join(no_invoice_folder, f))])
            if file_count > 0:
                print(f"  无发票号: {file_count} 个文件 -> {no_invoice_folder}")


if __name__ == "__main__":
    main()
