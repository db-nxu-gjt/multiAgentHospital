# 医院虚拟会诊系统 (VCS)

> 基于多智能体协作（Multi-Agent）的桌面端虚拟会诊平台，旨在提升医院会诊质量、缩短会诊周期、降低漏诊率。
> 
> **V1.1（2026-07-31）**：完成深度代码审查与修复，新增 88 个测试用例，核心模块覆盖率 86-100%，已打包为可执行程序。详见 [用户使用手册](doc/用户使用手册.md)。

---

## 项目概述

本系统是一套**辅助决策支持系统（CDSS）**，通过AI模拟多学科专家会诊，帮助临床医生快速获得规范化、循证化的会诊意见。系统定位为**辅助而非替代**人类医生的最终判断。

### 核心能力

- **病历自动整合**：从HIS、EMR、LIS、PACS等医院信息系统自动抽取并结构化患者数据
- **多智能体协作会诊**：模拟呼吸、心内、神经、内分泌、影像、药学等专科AI专家进行联合诊断
- **循证医学支持**：每条建议标注循证等级（A/B/C/D）和推荐强度
- **医学知识图谱**：基于症状-疾病-检查-药物关联网络提供鉴别诊断
- **会诊全流程管理**：申请、执行、报告生成、审核确认、归档闭环

---

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                     医院虚拟会诊系统                          │
├─────────────────────────────────────────────────────────────┤
│  表现层：PyQt6 桌面应用                                       │
│  ├─ 患者全景视图                                              │
│  ├─ 虚拟会诊工作台                                            │
│  ├─ 会诊报告查看器                                            │
│  └─ 医学知识图谱浏览器                                         │
├─────────────────────────────────────────────────────────────┤
│  核心引擎层                                                   │
│  ├─ 病历整合引擎（MedicalRecordIntegrator）                   │
│  ├─ 多智能体协作引擎（Agent + Moderator）                     │
│  ├─ 会诊流程引擎（ConsultationEngine）                        │
│  ├─ 医学知识图谱（MedicalKnowledgeGraph）                     │
│  └─ 循证等级与推荐系统（Evidence/Recommendation）              │
├─────────────────────────────────────────────────────────────┤
│  数据适配层                                                   │
│  ├─ HIS适配器                                                 │
│  ├─ EMR适配器                                                 │
│  ├─ LIS适配器                                                 │
│  ├─ PACS适配器                                                │
│  └─ 模拟适配器（用于测试/演示）                                │
├─────────────────────────────────────────────────────────────┤
│  数据层                                                       │
│  ├─ JSON病历文件                                              │
│  ├─ 医学知识图谱（内存/JSON）                                  │
│  └─ 会诊报告（JSON/Markdown）                                  │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术 |
|------|------|
| 桌面GUI | PyQt6 |
| 后端逻辑 | Python 3.12 |
| 数据处理 | pandas, numpy |
| 自然语言处理 | jieba |
| 机器学习 | scikit-learn |
| 测试 | pytest, pytest-cov |

---

## 快速开始

### 1. 环境准备

确保已安装 Python 3.10+，然后安装依赖：

```bash
pip install -r requirements.txt
```

### 2. 下载测试数据集

```bash
python scripts/download_datasets.py
```

该脚本会下载：
- UCI Cleveland Heart Disease 数据集
- Pima Indians Diabetes 数据集
- 医学QA样本数据

### 3. 启动桌面应用

```bash
python main.py
```

### 4. 命令行演示（无需GUI）

```bash
python demo.py
```

### 5. 打包为可执行程序

```bash
# 一键打包（包含测试、构建、验证）
python scripts/build_exe.py

# 或直接调用 PyInstaller
pyinstaller build.spec --clean --noconfirm
```

打包产物位于 `dist/医院虚拟会诊系统/`，双击 `医院虚拟会诊系统.exe` 即可启动。

---

## 项目结构

```
MultiAgentHospital/
├── doc/                              # 设计文档
│   ├── 医院虚拟会诊系统功能设计书.md
│   └── 用户使用手册.md                 # V1.1 新增
├── src/                              # 源代码
│   ├── core/                         # 核心引擎
│   │   ├── patient.py                # 患者数据模型
│   │   ├── medical_record.py         # 病历整合引擎
│   │   ├── agent.py                  # 专科智能体
│   │   ├── moderator.py              # 主持人智能体
│   │   ├── consultation.py           # 会诊引擎
│   │   ├── knowledge_graph.py        # 医学知识图谱
│   │   └── evidence.py               # 循证等级
│   ├── adapters/                     # 医院系统适配器
│   │   ├── base.py
│   │   ├── his_adapter.py
│   │   ├── emr_adapter.py
│   │   ├── lis_adapter.py
│   │   └── pacs_adapter.py
│   ├── ui/                           # PyQt6桌面界面
│   │   ├── main_window.py
│   │   ├── patient_view.py
│   │   ├── consultation_view.py
│   │   ├── report_view.py
│   │   └── knowledge_graph_dialog.py
│   └── utils/                        # 工具函数
│       └── data_loader.py            # 数据集加载器
├── tests/                            # 测试用例（116 个）
│   ├── test_patient.py
│   ├── test_medical_record.py
│   ├── test_agent.py
│   ├── test_consultation.py
│   ├── test_integration.py
│   ├── test_data_loader.py
│   ├── test_knowledge_graph.py       # V1.1 新增
│   ├── test_evidence.py              # V1.1 新增
│   ├── test_adapters.py              # V1.1 新增
│   ├── test_moderator.py             # V1.1 新增
│   └── test_edge_cases.py            # V1.1 新增
├── data/                             # 数据目录
│   ├── sample_cases.json             # 示例病例
│   ├── raw/                          # 下载的原始数据
│   └── processed/                    # 处理后的报告
├── scripts/                          # 工具脚本
│   ├── download_datasets.py
│   ├── debug_patient.py
│   └── build_exe.py                  # V1.1 新增：打包脚本
├── main.py                           # 桌面应用入口
├── demo.py                           # 命令行演示
├── build.spec                        # V1.1 新增：PyInstaller 配置
├── requirements.txt                  # Python依赖
└── README.md                         # 本文件
```

---

## 测试

### 运行全部测试

```bash
python -m pytest tests/ -v
```

### 运行覆盖率测试

```bash
python -m pytest tests/ --cov=src --cov-report=html
```

### 当前测试结果

- **测试用例**：116个（V1.1 新增 88 个）
- **通过情况**：全部通过 ✅
- **核心模块覆盖率**：
  - agent.py: 94%
  - consultation.py: 97%
  - evidence.py: 100%
  - knowledge_graph.py: 99%
  - moderator.py: 97%
  - patient.py: 97%
  - medical_record.py: 86%

---

## 使用说明

### 桌面端操作流程

1. **加载患者**：点击"加载示例病例"或"从JSON加载患者"
2. **查看全景视图**：在"患者全景视图"标签页查看整合后的病历
3. **发起会诊**：切换到"虚拟会诊"标签页，选择参与专家，填写临床问题
4. **执行会诊**：点击"开始虚拟会诊"，等待AI分析完成
5. **查看报告**：在"会诊报告"标签页查看结构化报告，可保存为JSON或Markdown
6. **审核确认**：医师审核报告后点击"审核确认"

### 模拟医院系统集成

系统内置 `MockHospitalAdapter`，可通过以下方式配置真实医院系统适配器：

```python
from src.adapters.his_adapter import HISAdapter
from src.adapters.emr_adapter import EMRAdapter
from src.core.medical_record import MedicalRecordIntegrator

integrator = MedicalRecordIntegrator()
integrator.add_adapter(HISAdapter({"endpoint": "http://his.hospital.com/api"}))
integrator.add_adapter(EMRAdapter({"endpoint": "http://emr.hospital.com/api"}))

patient = integrator.integrate("P001")
```

---

## 真实数据测试结果

系统已接入以下公开医学数据集进行测试验证：

### UCI Cleveland Heart Disease 数据集

- 使用真实心脏病数据构建虚拟患者
- 对冠心病患者，AI首选诊断为"冠状动脉粥样硬化性心脏病"（置信度约82%）
- 对非冠心病患者，AI未误诊为冠心病

### Pima Indians Diabetes 数据集

- 使用真实糖尿病筛查数据构建虚拟患者
- 系统能够识别血糖异常并推荐内分泌科会诊
- 能够生成包含糖尿病鉴别诊断的结构化报告

---

## 安全与合规声明

1. **辅助决策定位**：本系统仅为临床决策支持工具，不替代执业医师的诊断和治疗决策。
2. **数据安全**：患者敏感数据默认在本地处理，真实医院环境部署需遵循等保三级、个人信息保护法等法规。
3. **人工审核**：所有AI生成的会诊意见均需经主治医师审核确认后方可执行。
4. **审计追溯**：系统保留完整的会诊流程日志和报告版本记录。

---

## 后续优化方向

1. **接入真实大语言模型**：当前为基于规则的智能体，后续可接入 DeepSeek/通义千问等LLM增强推理能力
2. **扩展专科智能体**：增加肿瘤、血液、风湿免疫等更多专科Agent
3. **真实人类专家协作**：支持人类专家远程参与AI会诊讨论
4. **知识图谱扩充**：接入更多临床指南、药品说明书、罕见病数据库
5. **FHIR标准对接**：完善与医院现有HIS/EMR/LIS/PACS系统的FHIR互操作

---

## 许可证

本项目为医院内部研究用原型系统，未经授权不得用于商业用途。

---

> **作者**：资深软件架构师 / AI医疗系统设计师  
> **版本**：V1.0  
> **日期**：2026年7月31日
