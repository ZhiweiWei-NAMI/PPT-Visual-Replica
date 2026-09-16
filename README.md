# PPT Visual Replica

[English README](README.en.md)

把参考图片重建为可编辑 PowerPoint，也可根据论文、数据和教学材料制作科研汇报、课程演示与答辩。合并了 scientific-slides 的内容组织、科学图表和演讲指导；按任务选择原生图形、已有素材、矢量图或生成图片。

## 使用示例

```text
使用 $ppt-visual-replica 将这张参考图重建为可编辑 PPTX。
文字保留为文本框，简单图标与流程图尽量使用原生形状和连接线。
保留参考图的比例、层级和配色，交付前渲染检查。
```

```text
使用 $ppt-visual-replica 根据这些论文和实验图制作一份 15 分钟科研汇报。
说明研究问题、方法、主要结果和局限，保留真实数据和引用，
提供可编辑 PPTX；只在有助于解释时增加插图。
```

## 项目主视觉

![Hero visual placeholder](assets/readme/hero-visual.png)

## 三种常用任务

| 任务 | 做法 |
| --- | --- |
| 图片或信息图复刻 | 对照参考重建文字、布局和对象，按编辑需求选择素材类型 |
| 科研或教学演示 | 根据受众、时间和证据组织内容，核对图表、公式与引用 |
| 修改现有 PPT | 沿用模板和主题，检查修改页以及受共享样式影响的页面 |

不强制使用特定生图服务、整页位图、固定配图数量或名为 research-lookup 的工具。PPTX 中可移动的图片不等于图片内部的图形可编辑；交付时应明确两者的区别。

## 严格素材审计模式

原有逐素材生成、残差追踪、哈希与对象元数据检查保留为可选模式，仅在用户明确要求该工作流时启用。其脚本接口保持兼容。

- [默认技能入口](skill/ppt-visual-replica/SKILL.md)
- [参考图复刻](skill/ppt-visual-replica/references/reference-reconstruction.md)
- [科研与教学演示](skill/ppt-visual-replica/references/scientific-presentations.md)
- [严格素材工作流及数据约定](skill/ppt-visual-replica/references/strict-asset-workflow.md)

`build_pptx.py` 是严格模式的单页构建器，`validate_delivery.py` 检查该模式专用的交付目录。它们不是通用多页制作与验收工具。普通演示文稿应使用适合的 PowerPoint 库或应用工具，并完成渲染和可编辑性检查。

严格模式验证：

```text
python skill/ppt-visual-replica/scripts/validate_delivery.py --root <output-root>
```

## 工作流示意

![Workflow visual placeholder](assets/readme/workflow-visual.png)

上图展示原有严格复刻流程；普通演示文稿可按任务选择原生对象和已有素材。素材预览墙是新增的按需检查步骤。

## 素材预览墙（#2）

批量切图或复杂复刻时，可用 `asset_review.py` 并排查看参考裁剪和候选素材，检查细节丢失，并对照独立清单显示缺失项。默认由助手检查后继续；仅在用户要求时等待人工确认。

工具不会自动判定绿色细节是否被误删，也不会把生成预览墙当作审阅通过。重新运行会保留未变化素材的审阅记录；素材或参考内容变化时需要重新检查。路径替换使用明确映射，不按同名文件猜测。

见[操作说明](skill/ppt-visual-replica/references/asset-review.md)和[示例预览墙](examples/satellite-network/audit/asset_review_wall.png)。示例墙已重新生成，但所有素材仍标为待审阅，不能视作原示例重新验收通过。

## 安装

通过 Codex Skill Installer 安装：

```text
$skill-installer install https://github.com/ZhiweiWei-NAMI/PPT-Visual-Replica/tree/main/skill/ppt-visual-replica
```

或将仓库的 `skill/ppt-visual-replica` 目录复制到你的技能目录。升级已有安装时先保留个人改动，再替换对应文件。

原有 Python 辅助脚本使用 Python 3.10+、Pillow 和 python-pptx。运行技能校验器还需要 PyYAML。普通 PPT 制作的依赖由所选工具决定；视觉检查另需可用的 PowerPoint、LibreOffice 或其他渲染器。

## 验证

```text
python -m unittest discover -s tests -v
python skill/ppt-visual-replica/scripts/audit_skill.py --root skill/ppt-visual-replica
```

脚本测试不能代替最终演示文稿的渲染检查。没有可用渲染器时，应说明尚未验证的版面内容。

## 现有示例

以下示例来自合并前的严格复刻流程，保留用于展示；本次技能合并没有重新生成或重新验收这些示例。

| 示例 | 内容 |
| --- | --- |
| [satellite-network](examples/satellite-network/) | 异构卫星网络架构 |
| [medical-ai-pipeline](examples/medical-ai-pipeline/) | 多模态医学 AI 辅助诊断流程 |
| [manufacturing-scheduler](examples/manufacturing-scheduler/) | 智能制造多机器人协同调度 |

| 参考图片 | PowerPoint 对象选择截图 |
| --- | --- |
| ![Satellite reference](examples/satellite-network/reference/reference.png) | ![Satellite selected elements](assets/readme/satellite-selected-elements.png) |

## 许可

见 [LICENSE](LICENSE)。科研演示指导整合并重新编写了 scientific-slides 中的叙事、图表适配和演讲规划思路；未引入其外部生图脚本、模板或强制生图流程。

## Star History

<a href="https://www.star-history.com/?repos=ZhiweiWei-NAMI%2FPPT-Visual-Replica&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=ZhiweiWei-NAMI/PPT-Visual-Replica&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=ZhiweiWei-NAMI/PPT-Visual-Replica&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=ZhiweiWei-NAMI/PPT-Visual-Replica&type=date&legend=top-left" />
 </picture>
</a>
