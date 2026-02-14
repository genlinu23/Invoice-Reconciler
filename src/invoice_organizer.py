"""
发票自动整理工具 - 主程序
功能：读取发票图片，通过OCR+LLM识别信息，本地重命名文件
改进方案：两阶段处理 (OCR提取 + LLM分析)
"""
import os
import json
import argparse
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 导入新的两阶段提取模块
from invoice_extractor import extract_invoice_info

try:
    from pdf2image import convert_from_path
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("WARNING: pdf2image not installed, PDF files will be skipped.")
    print("   Install: pip install pdf2image pillow")

# 加载环境变量
load_dotenv()

# 这些变量现在由 invoice_extractor 管理
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen3-VL-235B-A22B-Instruct-FP8")

# 发票类型映射
INVOICE_TYPES = {
    "餐饮": ["餐饮", "餐费", "美食", "外卖", "食品"],
    "住宿": ["住宿", "酒店", "宾馆", "民宿"],
    "交通": ["交通", "打车", "滴滴", "出租", "火车", "高铁", "飞机", "机票"],
    "购物": ["购物", "商品", "零售"],
    "其他": []
}

def get_file_hash(file_path):
    """计算文件的MD5哈希值（用于识别已处理文件）"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def load_processed_files(folder_path):
    """加载已处理文件的记录"""
    record_file = os.path.join(folder_path, ".processed_files.json")
    if os.path.exists(record_file):
        try:
            with open(record_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_processed_file(folder_path, file_hash, file_name, invoice_number=None):
    """保存已处理文件的记录"""
    record_file = os.path.join(folder_path, ".processed_files.json")
    processed = load_processed_files(folder_path)
    processed[file_hash] = {
        "filename": file_name,
        "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "invoice_number": invoice_number
    }
    with open(record_file, "w", encoding="utf-8") as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)

def remove_processed_file(folder_path, file_hash):
    """从记录中删除已处理文件（用于output被删除的情况）"""
    record_file = os.path.join(folder_path, ".processed_files.json")
    processed = load_processed_files(folder_path)
    if file_hash in processed:
        del processed[file_hash]
        with open(record_file, "w", encoding="utf-8") as f:
            json.dump(processed, f, ensure_ascii=False, indent=2)

def is_invoice_number_duplicate(folder_path, invoice_number):
    """检查发票号码是否已存在

    Args:
        folder_path: 文件夹路径
        invoice_number: 发票号码

    Returns:
        tuple: (是否重复, 已存在的文件名)
    """
    if not invoice_number:
        return False, None

    processed = load_processed_files(folder_path)
    for file_hash, info in processed.items():
        existing_number = info.get("invoice_number")
        if existing_number and existing_number == invoice_number:
            return True, info.get("filename")

    return False, None

def is_file_processed(folder_path, file_path, output_dir=None):
    """检查文件是否已处理过（同时验证output文件是否还存在）"""
    file_hash = get_file_hash(file_path)
    processed = load_processed_files(folder_path)
    
    # 方法1：检查记录文件
    if file_hash in processed:
        # 额外验证：如果output目录存在，检查对应的输出文件是否还在
        if output_dir and os.path.exists(output_dir):
            found_in_output = False
            for output_file in os.listdir(output_dir):
                output_path = os.path.join(output_dir, output_file)
                if os.path.isfile(output_path):
                    try:
                        output_hash = get_file_hash(output_path)
                        if output_hash == file_hash:
                            found_in_output = True
                            break
                    except:
                        pass
            
            # 如果记录说已处理，但output中找不到，则删除记录，需要重新处理
            if not found_in_output:
                remove_processed_file(folder_path, file_hash)
                return False
        
        return True
    
    # 方法2：检查output目录是否已有相同哈希的文件（兼容之前处理的文件）
    if output_dir and os.path.exists(output_dir):
        for output_file in os.listdir(output_dir):
            output_path = os.path.join(output_dir, output_file)
            if os.path.isfile(output_path):
                try:
                    output_hash = get_file_hash(output_path)
                    if output_hash == file_hash:
                        # 找到了，补充记录
                        save_processed_file(folder_path, file_hash, os.path.basename(file_path))
                        return True
                except:
                    pass
    
    return False

def analyze_invoice(image_path, logger=None):
    """
    分析发票信息 - 使用改进的两阶段处理

    阶段1: OCR提取文本 (PaddleOCR)
    阶段2: LLM分析理解 (Qwen3-VL)
    阶段3: 验证Agent三重验证

    如果未安装PaddleOCR，会直接报错

    Args:
        image_path: 图片路径
        logger: 日志实例（可选）
    """
    # 使用新的两阶段提取模块
    return extract_invoice_info(image_path, mode="auto", logger=logger)

def rename_invoice(image_path, invoice_info, output_dir, logger=None):
    """根据识别信息重命名文件"""
    if not invoice_info:
        return False

    category = invoice_info.get("category", "发票")
    amount = invoice_info.get("amount", "0")

    # 获取文件扩展名
    ext = Path(image_path).suffix

    # 根据类型生成不同的文件名
    if category == "水单":
        # 水单：日期_金额_水单.jpg
        date = invoice_info.get("date", "未知日期")
        new_name = f"{date}_{amount}_水单{ext}"
        base_name = f"{date}_{amount}_水单"
    else:
        # 发票：金额_类型_发票.jpg
        inv_type = invoice_info.get("type", "其他")
        new_name = f"{amount}_{inv_type}_发票{ext}"
        base_name = f"{amount}_{inv_type}_发票"

    new_path = os.path.join(output_dir, new_name)

    # 如果文件名冲突，添加序号
    counter = 1
    while os.path.exists(new_path):
        new_name = f"{base_name}_{counter}{ext}"
        new_path = os.path.join(output_dir, new_name)
        counter += 1

    # 复制文件
    shutil.copy2(image_path, new_path)

    if logger:
        logger.file_output(new_name)
        if invoice_info.get("_confidence"):
            logger.detail("置信度", f"{invoice_info['_confidence']:.1%}")
    else:
        print(f"[OK] 已保存: {new_name}\n")

    return True

def process_single_file(image_path, output_dir, folder_path=None, logger=None):
    """处理单个文件"""
    # 检查是否已处理过
    if folder_path and is_file_processed(folder_path, image_path, output_dir):
        if logger:
            logger.info(f"跳过（已处理）: {os.path.basename(image_path)}")
        else:
            print(f"[SKIP]  跳过（已处理）: {os.path.basename(image_path)}\n")
        return False

    if logger:
        logger.start_file(os.path.basename(image_path))

    invoice_info = analyze_invoice(image_path, logger=logger)
    if invoice_info:
        # 检查发票号码是否重复
        invoice_number = invoice_info.get("invoice_number", "")
        if folder_path and invoice_number:
            is_dup, existing_file = is_invoice_number_duplicate(folder_path, invoice_number)
            if is_dup:
                if logger:
                    logger.warning(f"跳过（发票号码重复）: {os.path.basename(image_path)}")
                    logger.detail("发票号码", invoice_number)
                    logger.detail("已存在于", existing_file)
                else:
                    print(f"[SKIP]  跳过（发票号码重复）: {os.path.basename(image_path)}")
                    print(f"   发票号码 {invoice_number} 已存在于: {existing_file}\n")
                return False

        success = rename_invoice(image_path, invoice_info, output_dir, logger=logger)
        if success and folder_path:
            # 记录已处理（包括发票号码）
            file_hash = get_file_hash(image_path)
            save_processed_file(folder_path, file_hash, os.path.basename(image_path), invoice_number)

        if logger:
            logger.finish_file(os.path.basename(image_path), success=success)
        return success

    if logger:
        logger.finish_file(os.path.basename(image_path), success=False, message="分析失败")
    return False

def process_folder(folder_path, output_dir):
    """批量处理文件夹"""                                                                                                                            
    supported_formats = [".jpg", ".jpeg", ".png", ".pdf"]
    image_files = []
    
    for root, dirs, files in os.walk(folder_path):
        # 跳过output和matched_output目录
        if "output" in dirs:
            dirs.remove("output")
        if "matched_output" in dirs:
            dirs.remove("matched_output")
        for file in files:
            if Path(file).suffix.lower() in supported_formats:
                image_files.append(os.path.join(root, file))
    
    if not image_files:
        print("[ERROR] 未找到图片文件")
        return
    
    # 统计已处理和待处理
    processed_files = load_processed_files(folder_path)
    total_files = len(image_files)
    already_processed = sum(1 for f in image_files if is_file_processed(folder_path, f, output_dir))
    to_process = total_files - already_processed
    
    print(f"\n📁 找到 {total_files} 张图片")
    print(f"[OK] 已处理: {already_processed} 张")
    print(f"🆕 待处理: {to_process} 张\n")
    print("="*60)
    
    success_count = 0
    skipped_count = 0
    for idx, image_path in enumerate(image_files, 1):
        print(f"\n[{idx}/{total_files}]")
        
        # 检查是否已处理
        if is_file_processed(folder_path, image_path, output_dir):
            print(f"[SKIP]  跳过（已处理）: {os.path.basename(image_path)}")
            skipped_count += 1
            print("-"*60)
            continue
        
        invoice_info = analyze_invoice(image_path)
        if invoice_info and rename_invoice(image_path, invoice_info, output_dir):
            # 记录已处理
            file_hash = get_file_hash(image_path)
            save_processed_file(folder_path, file_hash, os.path.basename(image_path))
            success_count += 1
        print("-"*60)
    
    print(f"\n[OK] 完成！")
    print(f"   本次新处理: {success_count} 张")
    print(f"   跳过已处理: {skipped_count} 张")
    print(f"   总计成功: {already_processed + success_count}/{total_files} 张")
    print(f"📂 输出目录: {output_dir}")

def main():
    parser = argparse.ArgumentParser(description="发票自动整理工具")
    parser.add_argument("--file", help="处理单个文件")
    parser.add_argument("--folder", help="批量处理文件夹")
    parser.add_argument("--output", help="输出目录（默认为输入目录下的output文件夹）")
    
    args = parser.parse_args()
    
    # 确定输出目录：如果未指定，则在输入目录下创建output
    if args.output:
        output_dir = args.output
    elif args.folder:
        output_dir = os.path.join(args.folder, "output")
    elif args.file:
        output_dir = os.path.join(os.path.dirname(args.file), "output")
    else:
        output_dir = "./output"
    
    os.makedirs(output_dir, exist_ok=True)
    
    if args.file:
        if not os.path.exists(args.file):
            print(f"[ERROR] 文件不存在: {args.file}")
            return
        folder_path = os.path.dirname(args.file)
        process_single_file(args.file, output_dir, folder_path)
    elif args.folder:
        if not os.path.exists(args.folder):
            print(f"[ERROR] 文件夹不存在: {args.folder}")
            return
        process_folder(args.folder, output_dir)
    else:
        print("请指定 --file 或 --folder 参数")
        parser.print_help()

if __name__ == "__main__":
    main()
