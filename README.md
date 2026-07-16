
# PPT Visual Replica


[English README](README.en.md)

将扁平化信息图转化为可审计、可编辑的 PowerPoint 页面：文本与结构布局保持 PPT 原生可编辑；图标、设备、图表、屏幕等语义视觉按最小语义单元拆分为独立透明素材；残差、素材、对象元数据与渲染预览均须通过闭环验收。


## 推荐提示词

```text
使用 $ppt-visual-replica 重建本地图片。文字和结构几何使用 PPT 原生对象；所有语义非文本视觉使用 IMAGE GEN 按最小语义单元生成。仅在素材通过语义、边框、透明背景和风格检查后从残差中扣除；完成渲染对比和 fail-closed 验证后再交付。
```

## 项目主视觉

![Hero visual placeholder](assets/readme/hero-visual.png)

## 快速上手

本项目核心是通过以下规则由 AI Agent 智能重构页面：

* **文本内容**：使用 PPT 原生文本框，便于用户后续编辑。
* **布局版式**：使用 PPT 原生元素（如面板、分隔线、箭头、连接线等）。
* **语义视觉元素**：通过 IMAGE GEN 或其他支持图片输入的 API，提取为透明 PNG 格式。
* **最小语义单元**：图标、屏幕、图表、设备等均对应独立可选的 PPT 对象。
* **严格边界**：图标不是“基础 PPT 元素”；流程箭头必须使用原生连接线箭头元数据。
* **失败关闭**：缺失证据、`pending`、`to_verify`、残差与红框不一致、死素材或过期 QA 均判定为失败。

## v1.1.0：残差与验收闭环

本版本根据实际复刻与复审任务中反复出现的问题收紧了工作流，并正式澄清 [issue #1](https://github.com/ZhiweiWei-NAMI/PPT-Visual-Replica/issues/1) 所询问的残差循环语义：

* 明确残差图是未解决语义单元的批处理与覆盖账本，不会自动优化已验收素材。
* 只有通过语义一致性、最小单元隔离、边框完整性、透明背景和风格检查的 `accepted` 素材才允许从当前残差中扣除。
* 素材网格仅切割声明使用的单元格，并检测空素材、贴边截断和色键残留。
* 每个 PPT 图片对象写入 `semantic_unit_id` 元数据，图片只允许等比例 contain 缩放；流程箭头保持原生可编辑。
* 新增 `validate_delivery.py`，统一检查 JSON/JSONL、素材与裁剪引用、死文件、残差闭合、当前文件哈希、PPTX 对象元数据和参考图误嵌入。

最终验证命令：

```text
python skill/ppt-visual-replica/scripts/validate_delivery.py --root <output-root>
```

## 工作流示意

![Workflow visual placeholder](assets/readme/workflow-visual.png)

## 示例展示：Satellite 网络图

以下为典型主示例展示，左图为原始参考图片，右图为 PPT 复刻版（已全选元素截图）。示例为首次生成（Pass@1）结果，整体结构准确，但局部图标、细节及文字排版可能需要额外微调。

| 原始参考图                                                                      | PPT中全选可编辑元素                                                                   |
| -------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| ![Satellite reference](examples/satellite-network/reference/reference.png) | ![Satellite selected elements](assets/readme/satellite-selected-elements.png) |

## 更多典型案例

| 示例                                                             | 描述                  |
| -------------------------------------------------------------- | ------------------- |
| [`satellite-network`](examples/satellite-network/)             | 异构卫星网络架构图，典型科研示例。   |
| [`medical-ai-pipeline`](examples/medical-ai-pipeline/)         | 多模态医学 AI 辅助诊断流程图示例。 |
| [`manufacturing-scheduler`](examples/manufacturing-scheduler/) | 智能制造多机器人协同调度方案示例。   |

## 已知问题与改进建议

* 若原图存在大量小图标，自动切割和去背景可能产生边缘缺陷、截断、色键残留或语义错配。此类素材不得直接验收，应重新生成或重新切割，直至边框与主体完整。
* 中文文字渲染偶尔会出现轻微对齐偏差，主要原因是字体、字号、行距与 PowerPoint 渲染机制差异所致。若追求高保真度，建议在 PPT 中手动微调，或明确字号和行距要求给 Agent 进一步优化。

可参考的替换提示词：

```text
我已将授权替换图标存放至 assets/user-icons/ 文件夹。请仅替换对应语义单元 database_stack、server_rack、monitor_dashboard，保持原始锚点和最小语义可编辑粒度；在 asset_manifest.json 中记录 source_type=user_asset、来源与用户批准信息，并重新执行渲染和完整验证。
```

## Skill 安装方法

推荐通过 Codex Skill Installer 从 GitHub 仓库路径安装：

```text
$skill-installer install https://github.com/ZhiweiWei-NAMI/PPT-Visual-Replica/tree/main/skill/ppt-visual-replica
```

也可以手动克隆仓库并复制 skill 目录：

**Windows:**

```powershell
git clone https://github.com/ZhiweiWei-NAMI/PPT-Visual-Replica.git
Copy-Item -Recurse .\PPT-Visual-Replica\skill\ppt-visual-replica "$env:USERPROFILE\.codex\skills\"
```

**macOS/Linux:**

```bash
git clone https://github.com/ZhiweiWei-NAMI/PPT-Visual-Replica.git
mkdir -p ~/.codex/skills
cp -R PPT-Visual-Replica/skill/ppt-visual-replica ~/.codex/skills/
```

安装完成后，重启 Codex 以加载新 skill。




## Star History

<a href="https://www.star-history.com/?repos=ZhiweiWei-NAMI%2FPPT-Visual-Replica&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=ZhiweiWei-NAMI/PPT-Visual-Replica&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=ZhiweiWei-NAMI/PPT-Visual-Replica&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=ZhiweiWei-NAMI/PPT-Visual-Replica&type=date&legend=top-left" />
 </picture>
</a>
