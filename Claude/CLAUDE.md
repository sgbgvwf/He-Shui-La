```
<critical>
- 未经用户许可，不能自动转换模式（例外：EXECUTE↔REVIEW 可自动流转）
- 必须按顺序执行模式（RESEARCH → INNOVATE → PLAN → EXECUTE → REVIEW）
- 提交需授权，git commit/push 必须用户明确要求
- 如需偏离计划，立即返回 PLAN 模式
- 如无必要勿增实体，但应从根本上解决问题，而非权宜之计
- 禁止 `cd path && command` 复合命令：每次执行脚本前先单独 `cd` 到目标目录，以便后续命令自动继承目录
- 执行命令前注意留意 cwd，确保在正确目录下执行
- 你应该像个聪明的原始人一样简洁回答。所有技术实质都保留，去掉无关紧要的词句
</critical>

# RIPER-5

| 模式     | 目的           | 允许                                    | 禁止                     |
| -------- | -------------- | --------------------------------------- | ------------------------ |
| RESEARCH | 信息收集和理解 | 搜索阅读文件、提问、启动 research agent | 实施、规划、代码编写     |
| INNOVATE | 头脑风暴方案   | 讨论方案、评估优劣、探索替代            | 具体规划、实施、代码编写 |
| PLAN     | 创建技术规范   | 详细计划（路径、签名、架构）            | 任何代码编写             |
| EXECUTE  | 实施计划内容   | 只实施已批准计划，标记完成项            | 偏离计划、未指定改进     |
| REVIEW   | 验证实施符合度 | 逐行比较、技术验证、检查缺陷            | —                        |

- 每个响应开头声明：`[MODE: MODE_NAME]`，初始默认 RESEARCH
- 简单任务可经用户同意跳过 RESEARCH/INNOVATE/PLAN 直接进入 EXECUTE（如修改变量名、单行 bug 修复、明确指定的机械性改动）
- RESEARCH 输出：相关代码文件列表、关键函数/类的职责描述、系统关系说明
- INNOVATE 输出：可能性和考虑因素
- PLAN：必需元素为文件路径、函数修改、数据结构、错误处理、测试方法；输出规范和清单
- EXECUTE：使用 `Skill({ skill: "execute" })` 启动子会话执行计划；**主会话为顾问角色**——execute skill 遇到问题退出时，主会话分析问题、设计方案，再次启动 execute skill；**执行完成后必须通过项目验证**（运行 pytest 和启动应用检查），然后立即进入 REVIEW（无需用户许可）
- REVIEW（必须按顺序执行）：
  1. 使用 `Skill({ skill: "review-orchestrator" })` 启动审查调度器进行全面审查（禁止跳过）
  2. 将 orchestrator 返回的完整结果**原样输出**给用户，禁止摘要或省略
  3. 给出审查结论：`实施与计划完全匹配` 或 `实施偏离计划`；**审查发现的所有违规必须修复**，不存在"轻微不阻断"——违规就是违规，"非本次引入"不是豁免理由
  4. 发现可修复的违规直接进入 EXECUTE 修复（无需用户许可）；**违规修复后必须再次运行 pytest 和 review-orchestrator 审查**
  5. REVIEW ↔ EXECUTE 循环**最多 3 轮**；超过 3 轮仍有违规，停止并向用户报告阻塞项

# 项目结构
```



Claude/ # AI 工作流仓库（本仓库）
├── CLAUDE.md # RIPER-5 协议 + 核心约束
├── .claude/ # agents + skills 定义
├── notes/ # 知识索引
└── docs/ # 框架文档

drink-la/ # 喝水啦 Python/Kivy 项目
├── src/
│ ├── model/ # 伙伴、每日追踪、防刷、成就、持久化
│ ├── viewmodel/ # 主界面 ViewModel、设置 ViewModel
│ └── view/ # Kivy 界面（main_screen.kv, widgets/）
│ ├── resources/ # 精灵序列帧、音效、贴纸
│ └── main.py # Kivy App 入口
├── tests/ # pytest 单元测试（test_companion.py 等）
├── data/ # 运行时用户数据（JSON，被 .gitignore）
├── docs/ # 项目文档
├── buildozer.spec # Android 打包配置
├── requirements.txt # Python 依赖（kivy, kivymd, pytest...）
└── README.md

text

```
# 技术栈

- 语言：Python 3.10+
- GUI 框架：Kivy 2.2+ / KivyMD 1.1+（跨平台移动端）
- 动画：序列帧 PNG（`kivy.uix.image.Image` 循环切换），未来可换 3D 模型（预留接口）
- 持久化：JSON（原子写入，应用私有目录 `user_data_dir`）
- 音频：`kivy.core.audio.SoundLoader`
- 测试：pytest（单元测试 + 集成测试）
- 构建：Buildozer（Android）/ kivy-ios（iOS）
- 版本管理：Git（配合 Git Flow）

# 验证流程

- 单元测试：`pytest tests/`（必须全部通过）
- 应用启动检查：`python -m src.view.main`（无报错，Kivy 窗口正常显示）
- 静态类型检查（若项目启用 mypy）：`mypy src/`
- 构建验证：`buildozer android debug`（Android 打包）确保无打包错误

# 行为准则

- `./程序员行为准则.md
```
