# IFLOW.md - nnsplace 项目指南

## 项目概述

nnsplace 是一个用于 FPGA（现场可编程门阵列）布局的 Python 项目，全称为 "Affordable Placement Python Code (for FPGA)"。该项目旨在优化电子电路设计中电路组件（模块）在网格状结构上的放置，目标是最小化连接组件之间的最长线长（worst wire length）。

该项目使用 PyScaffold 4.1.1 构建，采用 "No Non-Sense"（NNS）布局算法，通过 Howard 算法、合法化和 I/O 垫分配等步骤来优化布局。

## 技术栈和依赖

- **Python**: 项目主要编程语言
- **NetworkX**: 用于图结构表示和算法（特别是二分图最小权重完全匹配）
- **SciPy**: NetworkX 的二分图匹配功能需要 SciPy
- **Decorator**: 用于装饰器功能
- **外部依赖**:
  - luk036/mywheel
  - luk036/digraphx
  - luk036/physdes-py
  - luk036/netlistx

## 核心功能

1. **布局算法**: 实现了基于网络流图的布局算法，使用 Howard 算法进行优化
2. **合法化**: 确保模块不重叠并符合网格约束
3. **I/O 垫分配**: 将输入/输出连接分配到网格边缘
4. **优化循环**: 沿 X 和 Y 轴重复优化和合法化，直到达到最佳布局

## 文件结构

- `src/nnsplace/`: 源代码目录
  - `placement.py`: 核心布局算法实现
  - `placement_cfg.py`: 布局配置类
  - `netlist.py`: 网表处理
  - 其他算法文件（如 `min_parametric.py`, `neg_cycle.py` 等）
- `tests/`: 测试代码
- `outputs/`: 输出的 SVG 图像文件，显示布局结果
- `requirements/`: 依赖管理文件
- `experiments/`: 实验代码

## 安装和运行

### 开发环境设置

```bash
pip3 install -r ./requirements.txt
pip3 install git+https://github.com/luk036/mywheel.git
pip3 install git+https://github.com/luk036/digraphx.git
pip3 install git+https://github.com/luk036/netlistx.git
pip3 install git+https://github.com/luk036/physdes-py.git
python3 setup.py develop
```

### 依赖说明

- `requirements/default.txt`: 包含运行时依赖（networkx, scipy, decorator）
- `requirements/test.txt`: 包含测试依赖（pytest, coverage 等）
- 外部依赖通过 Git URL 安装

## 开发约定

- 使用 `setup.py develop` 进行开发安装
- 项目遵循 Python 编码标准
- 测试代码位于 `tests/` 目录
- 文档通过 readthedocs 维护

## 关键算法

- **Howard 算法**: 用于优化模块沿每个轴的位置
- **二分图匹配**: 用于布局合法化，解决模块重叠问题
- **参数最小成本流算法**: 核心优化算法
- **最坏循环比算法**: 用于某些优化步骤

## 输出示例

项目生成 SVG 图像文件显示布局过程:
- 初始布局: `outputs/initial.svg`
- 合法化后: `outputs/after1legalize.svg`
- 最终布局: `outputs/final.svg`

## 配置参数

`NnsConfig` 类定义布局配置:
- `grid`: 网格尺寸 (x, y)
- `delta`: X 和 Y 轴的增量值 (delta_x, delta_y)

## 布局流程

1. 从网表创建流图
2. 生成初始随机布局
3. 使用 NNS 方法迭代优化:
   - 沿轴应用 Howard 算法
   - 合法化布局以确保无重叠
   - 分配 I/O 垫
4. 重复优化直到满足迭代次数或无进一步改进
