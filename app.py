"""
发票整理工具 - 简化版
功能：提取发票信息，按金额和类型重命名文件
"""
import os
import sys
import json
from pathlib import Path
from shutil import copy2

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from invoice_extractor import extract_invoice_info


def process_invoice_folder(input_folder, output_folder=None):
    """
    处理发票文件夹

    Args:
        input_folder: 输入文件夹路径
        output_folder: 输出文件夹路径（可选，默认为input_folder/output）

    Returns:
        dict: 处理统计信息
    """
    # 设置输出文件夹
    if not output_folder:
        output_folder = os.path.join(input_folder, "output")

    os.makedirs(output_folder, exist_ok=True)

    # 支持的格式
    supported_formats = [".jpg", ".jpeg", ".png", ".pdf"]

    # 获取所有图片文件
    image_files = []
    for root, dirs, files in os.walk(input_folder):
        # 跳过输出目录
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
        filename = os.path.basename(file_path)
        print(f"\n[{idx}/{len(image_files)}] {filename}")

        try:
            # 提取发票信息
            invoice_info = extract_invoice_info(file_path)

            if not invoice_info:
                print("   [SKIP] 提取失败")
                stats["failed"] += 1
                continue

            # 提取信息
            amount = invoice_info.get("amount", "0")
            inv_type = invoice_info.get("type", "其他")
            date = invoice_info.get("date", "")

            # 转换金额
            try:
                amount_float = float(amount)
                stats["total_amount"] += amount_float
            except:
                amount_float = 0.0

            # 统计类型
            if inv_type not in stats["by_type"]:
                stats["by_type"][inv_type] = {"count": 0, "amount": 0.0}
            stats["by_type"][inv_type]["count"] += 1
            stats["by_type"][inv_type]["amount"] += amount_float

            # 生成新文件名：金额_类型_日期.ext
            file_ext = Path(file_path).suffix
            if date:
                new_filename = f"{amount}_{inv_type}_{date}{file_ext}"
            else:
                new_filename = f"{amount}_{inv_type}{file_ext}"

            # 创建分类文件夹
            type_folder = os.path.join(output_folder, inv_type)
            os.makedirs(type_folder, exist_ok=True)

            # 处理重名
            new_path = os.path.join(type_folder, new_filename)
            counter = 1
            while os.path.exists(new_path):
                if date:
                    new_filename = f"{amount}_{inv_type}_{date}_{counter}{file_ext}"
                else:
                    new_filename = f"{amount}_{inv_type}_{counter}{file_ext}"
                new_path = os.path.join(type_folder, new_filename)
                counter += 1

            # 复制文件
            copy2(file_path, new_path)
            # 显示相对路径
            rel_path = os.path.join(inv_type, new_filename)
            print(f"   [OK] -> {rel_path}")
            stats["success"] += 1

        except Exception as e:
            print(f"   [ERROR] 处理失败: {e}")
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
    """主函数"""
    print("="*60)
    print("发票整理工具 - 简化版")
    print("功能：提取发票信息，按金额和类型重命名")
    print("="*60)

    # 获取输入文件夹
    if len(sys.argv) > 1:
        input_folder = sys.argv[1]
    else:
        input_folder = input("请输入发票文件夹路径: ").strip()

    # 检查文件夹
    if not os.path.exists(input_folder):
        print(f"[ERROR] 文件夹不存在: {input_folder}")
        return

    # 获取输出文件夹（可选）
    if len(sys.argv) > 2:
        output_folder = sys.argv[2]
    else:
        output_folder = None

    # 处理文件夹
    stats = process_invoice_folder(input_folder, output_folder)

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
