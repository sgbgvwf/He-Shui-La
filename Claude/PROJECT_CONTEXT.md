```
 项目概览

此文件为项目上下文的核心路由文档，指引 AI 在何处读取相应的文档。

## 项目简介

喝水啦 — 专为 3-8 岁儿童设计的移动端喝水习惯养成游戏，基于 Python + Kivy 框架开发，完全离线运行，无网络、无广告、无社交。

## 快速开始

### 运行项目

在项目根目录（`drink-la/`）执行：
```bash
python -m src.view.main
```



或直接运行入口脚本：

bash

```
python src/view/main.py
```



确保已安装依赖（见 `requirements.txt`）。

### 运行测试

使用 pytest 运行单元测试：

bash

```
pytest tests/
```



如需覆盖率报告：

bash

```
pytest --cov=src tests/
```



### 打包移动端

Android（使用 Buildozer）：

bash

```
buildozer android debug
```



iOS（使用 kivy-ios）：

bash

```
toolchain build kivy
toolchain create drink_la src/view/main.py
```



## 最近变更

详细变更日志见 [docs/CHANGELOG.md](https://docs/CHANGELOG.md)（待补充）。

**当前状态（2026-07-07）**：

- 📄 完成项目设计文档 v4.9（子供向细化，功能框架完整）
- 🏗 确立 MVVM 架构（Model-ViewModel-View），核心 Model 类规划完成
- 🎨 占位美术资源（序列帧、音效、贴纸）待后续替换
- 📊 数值与名称（进化形态、成就、水分状态）由策划后期填充

## 文档导航

根据任务类型查阅对应文档：

- 项目设计文档 → [喝水提醒器——Python 桌面应用项目设计文档 (2).md](喝水提醒器——Python 桌面应用项目设计文档 (2).md)
- 项目 README → [README.md](https://readme.md/)（待完善）
- 技术选型与架构 → 设计文档第 3 章
- 数据持久化方案 → 设计文档第 6 章
- 用户界面与交互 → 设计文档第 7 章
- 变更日志 → [docs/CHANGELOG.md](https://docs/CHANGELOG.md)（待创建）
- 知识索引 → [notes/INDEX.md](https://notes/INDEX.md)（待创建）

### 行为准则（必须遵守）

| 文件                                                         | 适用场景                       |
| :----------------------------------------------------------- | :----------------------------- |
| [程序员行为准则.md](https://xn--siq59feh92ft5tfg4b43u.md/)   | 所有代码编写（Python/Kivy 版） |
| [游戏策划行为准则.md](https://xn--siq59fqg4a686pwvqw5upwx.md/) | 玩法/数值设计                  |
| [Review行为准则.md](https://xn--review-1y7i85vmva1944b.md/)  | 代码审查                       |
| [评论行为准则.md](https://xn--siq59fehu72qoudyb.md/)         | GitHub Issue/PR 评论           |

### 框架详细文档

- RIPER-5 流程：[.claude/skills/riper5/SKILL.md](https://.claude/skills/riper5/SKILL.md)
- 审查调度：[.claude/skills/review-orchestrator/SKILL.md](https://.claude/skills/review-orchestrator/SKILL.md)
