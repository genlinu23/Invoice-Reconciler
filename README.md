# 发票整理工具

智能发票信息提取和整理系统

## 功能简介

本工具使用 OCR + LLM 技术，自动提取发票信息并按金额和类型重命名文件。

核心功能：
- ✅ OCR文本提取（PaddleOCR）
- ✅ LLM智能分析（Qwen3-VL）
- ✅ 自动提取金额
- ✅ 智能分类（餐饮/交通/住宿/其他）
- ✅ 按金额和类型重命名文件
- ✅ 批量处理整个文件夹
- ✅ 自动统计金额

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置API

编辑 `.env` 文件，配置LLM API：

```env
API_BASE_URL=http://45.120.102.120:10021/v1/chat/completions
API_KEY=your-api-key
MODEL_NAME=Qwen3-VL-235B-A22B-Instruct-FP8
```

### 3. 运行程序

```bash
python app.py
```

或者指定文件夹：

```bash
python app.py "发票文件夹路径"
```

指定输出文件夹：

```bash
python app.py "发票文件夹路径" "输出文件夹路径"
```

## 使用流程

1. 准备发票文件夹（支持 JPG、PNG、PDF 格式）
2. 运行 `python app.py`
3. 输入发票文件夹路径
4. 等待处理完成
5. 查看输出文件夹中的重命名文件

## 输出格式

处理后的文件会按以下格式重命名：

```
168.01_餐饮_20240115.pdf
45.50_交通_20240116.jpg
280.00_住宿_20240117.png
```

格式：`金额_类型_日期.扩展名`

## 统计信息

处理完成后会生成 `statistics.json`，包含：
- 总文件数
- 成功/失败数量
- 总金额
- 按类型统计

示例：

```json
{
  "total": 10,
  "success": 9,
  "failed": 1,
  "total_amount": 1234.56,
  "by_type": {
    "餐饮": {"count": 5, "amount": 500.00},
    "交通": {"count": 3, "amount": 234.56},
    "住宿": {"count": 1, "amount": 500.00}
  }
}
```

## 项目结构

```
发票整理工具/
├── src/                          # 核心代码
│   ├── invoice_extractor.py      # OCR + LLM 提取引擎
│   ├── invoice_organizer.py      # 文件整理逻辑
│   └── logger.py                 # 日志模块
├── app.py                        # 主程序
├── .env                          # API配置文件
├── requirements.txt              # Python依赖
└── README.md                     # 本文档
```

## 技术栈

- **OCR**: PaddleOCR
- **LLM**: Qwen3-VL (通过 OpenAI-compatible API)
- **语言**: Python 3.8+

## 支持的文件格式

- JPG / JPEG
- PNG
- PDF（仅第一页）

## 支持的发票类型

- 餐饮发票（餐厅、饭店、咖啡店等）
- 交通发票（打车、火车、飞机等）
- 住宿发票（酒店、宾馆等）
- 其他发票（不符合以上类别的）

## 注意事项

1. 需要配置有效的 LLM API 密钥
2. 首次运行会下载 PaddleOCR 模型
3. PDF 文件需要安装 poppler
4. 处理大量文件时需要等待

## 常见问题

**Q: 如何处理 PDF 文件？**
A: 工具会自动将 PDF 第一页转换为图片进行识别

**Q: 识别失败怎么办？**
A: 检查图片清晰度，确保文字清晰可读

**Q: 如何修改分类规则？**
A: 编辑 `src/invoice_extractor.py` 中的 LLM prompt

**Q: 支持批量处理吗？**
A: 是的，会自动处理指定文件夹下的所有图片

## 更新日志

### v2.0 (2026-02-12)
- ✅ 简化项目结构
- ✅ 删除水单相关功能
- ✅ 专注于发票信息提取
- ✅ 优化金额计算和统计

### v1.0
- ✅ 基础发票提取功能
- ✅ OCR + LLM 双重识别
- ✅ 自动分类和重命名

---

**开发**: Claude Code
