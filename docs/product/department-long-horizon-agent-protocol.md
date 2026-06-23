# 部门汇报：长程 Agent 的状态协议与管理面

LoopX 当前最值得对外讲清楚的，不是又多了一个 todo
列表，也不是把心跳调得更勤。真正的产品判断是：长程 Agent
要跨天、跨线程、跨 agent 继续工作，必须把目标、待办、证据、门控、
额度、回滚和人的判断，沉淀成一套可继承的状态协议。

这份文档面向部门级别汇报，基于仓库已有实现和自迭代积累，收敛三件事：

1. 长程 Agent 从接入、运行到收尾需要哪些核心状态。
2. LoopX 已经沉淀出的任务流转范式，哪些值得优先讲。
3. 接下来如何把三路 agent 并发、自迭代、人类 gate 和可回滚能力，做成可展示、可管理、可继续演进的产品面。

## 1. 当前判断

长程 Agent 的关键问题不是“让模型更久地跑”，而是“让下一次醒来的人或
agent 仍然知道现在该不该跑、能跑什么、跑完怎么算数”。

因此 LoopX 的核心状态协议应该从聊天上下文里搬出来，成为项目级事实：

- `goal` 记录长期目标和边界。
- `todo` 记录可执行工作单元和所有权。
- `gate` 记录需要人判断的边界，而不是一句松散的聊天提醒。
- `run/event` 记录每次推进、验证、失败、修复和交接。
- `quota` 记录什么时候该醒、什么时候该安静、什么时候该停止制造噪音。
- `projection` 把内部状态翻译成用户、agent、dashboard 都能看的界面。
- `reward/correction` 记录用户的管理判断，影响后续排序和工作方式。
- `rollback` 记录如何撤回代码、状态、证据或决策影响。

仓库里这些能力已经分散存在，下一步不是再写一份抽象白皮书，而是把它们
整理成一个部门能听懂、工程能落地、前端能展示的协议层。

## 2. 仓库已经具备的基础

| 能力 | 已有资产 | 当前价值 |
| --- | --- | --- |
| 三方状态模型 | [`docs/state-interaction-model.md`](../state-interaction-model.md) | 已定义 user、agent、state/dashboard 的职责边界。 |
| todo 协议 | [`docs/project-agent-todo-contract.md`](../project-agent-todo-contract.md) | 已有 `task_class`、`action_kind`、`claimed_by`、deferred/resume 等任务语义。 |
| 运行额度 | [`docs/quota-allocation.md`](../quota-allocation.md) | 已把自动化从“定时触发”提升为 `should-run` 和 `spend` 的状态协议。 |
| 状态投影 | [`docs/status-data-contract.md`](../status-data-contract.md) | 已有 `goal_channel_projection_v0`、todo/gate/lease/run projection。 |
| 心跳接入 | [`docs/heartbeat-automation-prompt.md`](../heartbeat-automation-prompt.md) | 已形成薄 prompt 加 registry/active-state 的执行模式。 |
| 任务图 | [`docs/reference/protocols/task-graph-projection-v0.md`](../reference/protocols/task-graph-projection-v0.md) | 已有 read-only 图结构思路，可表达 blocks、validates、handoff、supersedes。 |
| 前端管理面 | [`docs/product/frontstage-dashboard-interaction-baseline.md`](frontstage-dashboard-interaction-baseline.md) 与 [`apps/dashboard/src/views/frontstage-page.tsx`](../../apps/dashboard/src/views/frontstage-page.tsx) | 已有 user todo、agent todo、role map、active claims、open gates、timeline 的 ops 入口。 |
| 自迭代案例 | [`docs/showcases/cases/0619-loopx-self-iteration.md`](../showcases/cases/0619-loopx-self-iteration.md) | 已有高频 commit、多 lane、控制面修复、benchmark/product 化的真实故事。 |
| rollout 事件 | [`loopx/rollout_event_log.py`](../../loopx/rollout_event_log.py) | 已有 public-safe 事件记录、summary 和 event kind 分类。 |

这些资产说明，LoopX 已经不是“提醒 agent 继续干活”的脚本，而是一个初步的长程任务控制面。

## 3. 全流程状态协议

部门汇报里可以把协议讲成三段：启动、过程、结局。

### 3.1 启动协议

启动阶段要回答：这个项目是谁的，目标是什么，能不能接入，接入后先做什么。

| 状态 | 作用 | 仓库对应 |
| --- | --- | --- |
| `goal_identity` | 长程任务身份，包含 `goal_id`、项目路径、主控 agent、支持模式。 | registry、active state、`agent-profile-contract` |
| `connection_state` | 当前项目是 connect、bootstrap、只读复用，还是缺状态。 | `loopx connect`、`loopx bootstrap`、doctor |
| `local_state_boundary` | `.loopx/`、`.codex/goals/`、`.local/` 等本地状态不得误提交。 | integration / getting-started / install docs |
| `agent_registry` | 主控、旁路、产品能力等 agent 的身份、scope、worktree policy。 | `claimed_by`、primary/side-agent contract |
| `candidate_queue` | 接入后由用户的 agent 生成候选 todo，而不是 LoopX 自动塞 backlog。 | `todo-suggestion-prompt-v0` |
| `heartbeat_policy` | 接入后装 heartbeat，但仍由 quota 和 gate 决定是否推进。 | `heartbeat-prompt --thin`、quota |

启动的产品承诺应该是：新项目 5 分钟内接入，列出若干候选 todo，用户接受后即开始 loop。

### 3.2 过程协议

过程阶段要回答：现在该不该跑，跑哪个 todo，谁负责，能不能越过人类 gate，完成后怎么证明。

| 状态 | 作用 | 关键字段 |
| --- | --- | --- |
| `interaction_contract` | 每次心跳前的执行合同。 | `should_run`、`action_required`、`delivery_allowed`、`quiet_noop_allowed` |
| `todo_lifecycle` | 正式工作单元的生命周期。 | `open`、`claimed_by`、`task_class`、`action_kind`、`resume_when` |
| `lane_claim` | 多 agent 并行时的所有权和工作区边界。 | `primary_agent`、`side_agent`、`claimed_by`、worktree guard |
| `human_gate` | 人类决策，不是普通 todo。 | `decision_scope`、`gate_id`、`blocks`、`approval/rejection` |
| `run_event` | 每次推进、验证、失败、repair、handoff 的事实记录。 | run history、rollout event log |
| `evidence_ref` | 只记录 public-safe 证据指针，避免提交原始私密材料。 | artifact refs、summary、source refs |
| `quota_spend` | 只有 validated writeback 后才消耗自动化额度。 | `quota spend-slot` |
| `reward_signal` | 用户纠偏和管理评价，影响后续排序，而不是直接授权危险动作。 | reward/correction docs |

过程协议的核心味道是：agent 可以主动，但不能自说自话。每次推进都要能回到同一组问题：

1. 是否还有用户 gate。
2. 是否有 runnable agent todo。
3. 这次推进是否在 agent scope 内。
4. 是否产生了可验证产物。
5. 是否写回状态并消耗额度。

### 3.3 结局协议

结局阶段要回答：这个长程任务是完成、暂停、失败、转交，还是进入下一轮。

| 状态 | 作用 |
| --- | --- |
| `delivery_outcome` | 区分 `surface_only`、`outcome_progress`、`primary_goal_outcome` 等结果层级。 |
| `validation_result` | 记录测试、smoke、review、用户验收或 benchmark 证据。 |
| `successor_todo` | 完成后如果还有下一步，写成明确 successor，而不是留在 prose reason 里。 |
| `archive_or_pause` | 没有 runnable work 时安静，不把沉默误读成失败。 |
| `publication_boundary` | PR、文档、demo、公开 claim 必须有独立边界。 |
| `rollback_packet` | 如果结果需要撤回，能从 todo、commit、event、decision 找到补偿动作。 |

结局协议让“长期任务结束”不再等于“最后一条聊天消息”，而是项目状态可以被后来者继承。

## 4. 任务流转范式

[`docs/interaction-pattern-catalog.md`](../interaction-pattern-catalog.md) 已经很丰富，但部门汇报不应该逐条念 catalog。建议收敛成六类，按重要性排序。

### P0 范式一：有界推进和证据写回

每次自动化都必须是一个 bounded batch。它要么推进一个明确 todo，要么写回明确 blocker，要么安静。完成后必须有 validation 和 writeback，再决定是否 spend quota。

这个范式服务的是信任：用户看到的不是“agent 又跑了一轮”，而是“哪个工作单元变了，证据在哪里”。

### P0 范式二：Human gate 是状态，不是聊天提醒

Human in the loop 不是频繁打扰用户，而是把人的判断变成可投影、可恢复、可影响后续排序的 gate。

典型 gate 包括：

- 选择候选 todo 是否 promote。
- 授权 private material、外部发布、生产动作、破坏性 git。
- 对产物给 reward/correction。
- 改变目标优先级或 agent scope。

好的 human gate 必须有 `decision_scope`、阻塞的 todo、第一安全动作和拒绝后的 fallback。

### P0 范式三：多 agent lane 和所有权

长程任务很容易变成多个 agent 同时干。LoopX 的关键是让它们不是抢同一段上下文，而是在同一个 goal 下各自 claim、各自 worktree、各自写回。

部门演示里的三条 lane 可以定义为：

- 主控：目标路由、merge/review、最终收口。
- 旁路：独立实现或验证 slice。
- 产品能力：场景分析、协议抽象、前端/展示/管理面。

lane 之间的关系不靠口头记忆，而靠 `claimed_by`、handoff todo、review todo、rollout event 和 active claim 投影。

### P0 范式四：被 gate 阻塞时继续安全工作

如果 P0 被用户 gate 阻塞，agent 不应该制造无意义通知，也不应该完全停摆。CLI contract 允许时，可以继续 P1/P2 的安全可验证工作。

这服务的是效率：人的注意力只用在需要人的地方，机器时间用在仍然安全的地方。

### P1 范式五：没有候选时要诚实，也要能自修复

“没有 runnable todo”可能是真的，也可能是状态投影漏了 deferred、claim、resume 条件或 scope。LoopX 需要把 no-candidate、deferred-ready、projection-gap 区分开。

这服务的是可靠性：系统安静是因为真的无事可做，而不是因为状态没投出来。

### P1 范式六：外部信号必须先进状态面，再变成执行

repo issue、PR、公开社媒、私聊素材、实验结果看起来不同，但底层都要先回答：

- 能不能读。
- 读到什么粒度。
- 谁 gated。
- 能不能生成候选 todo。
- 下一步安全动作是什么。

因此 connector 的第一产物不应是“自动执行”，而是 source/status/candidate/gate 的状态面。

## 5. 前端展示方案

部门展示要避免“漂亮 packet”。用户真正要看的是：LoopX 如何把长程任务推进成真实产物，同时把人类交互、风险和证据放在正确位置。

### 5.1 推荐展示结构

前端应展示一条自迭代故事线：

1. 顶部：goal、当前状态、最近 24 小时进展、当前 user gate、下一安全动作。
2. 中部：三条 agent lane，分别展示主控、旁路、产品能力的 claimed todo、状态变化、最近证据。
3. 中部叠加：human gate 作为时间线上独立节点，显示它阻塞了什么、释放了什么、改变了什么。
4. 右侧：rollback 和风险面板，显示可撤回的 commit/todo/run/decision 关系。
5. 底部：rollout timeline，按事件展示 todo add、claim、complete、quota、validation、merge、repair。

### 5.2 当前历史状态是否足够

当前状态足够做一个“实时控制台”：`goal_channel_projection_v0`
能显示 top agent todo、user todo、active claim、open gate、recent events。
[`frontstage-page.tsx`](../../apps/dashboard/src/views/frontstage-page.tsx) 也已经有 ops route 的基础组件。

但当前历史状态还不足以做一个“漂亮且可信的三 agent 自迭代动画”。主要缺口是：

- `recent_events` 窗口太短，不能还原完整故事线。
- status projection 更偏当前快照，不保存每次 todo 的 before/after。
- rollout event 已有 `event_kind`、`agent_id`、`todo_id`、`status`、`classification`、`artifact_refs`，但还缺少显式因果边。
- 当前 projection 不一定包含历史 human gate，即使 gate 曾经影响路线，前端也难解释“人类交互改变了什么”。
- 多 agent lane 的角色、handoff、review、self-merge 与 rollback 关系还需要被结构化投影。

因此前端展示前要先做三个准备工作。

### 5.3 三个准备工作

| 顺序 | 准备工作 | 验收标准 |
| --- | --- | --- |
| `P0-prep-1` | 补强 rollout event 字段。 | 每个关键事件能表达 `from_state`、`to_state`、`caused_by`、`gate_id`、`lane_id`、`commit_ref`、`pr_ref`、`revert_of`。 |
| `P0-prep-2` | 生成 public-safe 三 agent 自迭代 fixture。 | fixture 能覆盖主控、旁路、产品能力三条 lane，包含至少一个 human gate 和一个 handoff/review 节点。 |
| `P0-prep-3` | 做 frontstage sufficiency check。 | smoke 能证明真实 projection 或 fixture 可以渲染 todo flow、human gate、evidence、rollback hint。 |

这三个准备工作完成后，前端才适合进入视觉 polish。否则展示会变成“UI 很好看，但状态故事不够硬”。

## 6. 长程任务可回滚能力

“commit 到 todo 的关系”是回滚能力的骨架，但不是全部。长程任务的回滚至少有五层。

| 层 | 回滚对象 | 推荐方式 |
| --- | --- | --- |
| 代码层 | commit、PR、branch | 用 git revert 或新修复 commit，并在 commit message/PR body 关联 todo。 |
| 控制面层 | todo、claim、active state | 不手改历史，追加 supersede/correction/restore checkpoint 事件。 |
| 证据层 | run、validation、benchmark 结论 | 标记 invalidated/superseded，保留原始 public-safe summary。 |
| 决策层 | user reward、approval、priority | 追加新的 decision/correction overlay，旧判断不删除。 |
| 展示层 | dashboard、showcase、公开 claim | 更新 publication gate 和 rollback notice，避免旧 demo 继续误导。 |

建议新增 `rollback_packet_v0`，字段包括：

- `rollback_id`
- `goal_id`
- `todo_ids`
- `commit_refs`
- `run_ids`
- `event_ids`
- `decision_ids`
- `reason`
- `safety_class`
- `proposed_action`
- `validation_plan`
- `requires_human_decision`
- `successor_todo`

产品原则是：回滚不是“把历史擦掉”，而是产生一个可审计的补偿动作。这样长程任务的失败、撤回、改路线，都能继续被后续 agent 理解。

## 7. 用户作为管理者的命令面

用户不应该只能追问每个线程“你现在干到哪了”。LoopX 应该支持管理者视角的全局命令，默认只读，必要时再显式 promote 或 approve。

建议先设计这些命令：

| 命令 | 读取状态 | 输出 |
| --- | --- | --- |
| `/loop-global-summary 最近一天进展` | 全局 registry、各 goal status、run history、quota、todo index。 | 最近完成了什么、当前卡点、活跃 agent、下一步建议。 |
| `/loop-global-gates` | open user gates、deferred-ready、decision scopes。 | 需要用户判断的事项，按阻塞价值排序。 |
| `/loop-global-agents` | agent profile、claimed todos、active leases、latest event、workspace guard。 | 每个 agent 在干什么、是否健康、是否越界。 |
| `/loop-global-todos --priority P0` | todo index、task class、claim、resume_when。 | 当前 P0 队列、谁负责、哪个能跑、哪个要等。 |
| `/loop-global-risks 最近一天` | projection warnings、private-boundary warnings、dirty worktree、no-progress streak、quota anomalies。 | 管理者应该先看的风险。 |
| `/loop-global-rollout loopx-meta 最近一天` | rollout event log、run history、PR/commit refs。 | 一条可读 timeline，用于复盘和部门汇报。 |
| `/loop-global-review-packet loopx-meta` | status projection、todo graph、recent outcomes、open gates、evidence refs。 | 给主控或用户的一页式 review packet。 |

这些命令的产品边界很重要：默认不写状态、不执行任务、不替用户批准 gate。写入类命令必须要求 `--apply` 或明确 user decision。

## 8. P0 推进队列

这次规划对应的 P0 队列分为两类：三个准备工作和六个正式建设项。

| 顺序 | 项目 | 目的 |
| --- | --- | --- |
| `P0-prep-1` | 补强 rollout-event log 字段。 | 让三 agent todo/gate/status 转换能被重放。 |
| `P0-prep-2` | 生成 public-safe 三 agent 自迭代 fixture。 | 让前端和部门汇报有真实故事，不依赖私密日志。 |
| `P0-prep-3` | 做 frontstage/status sufficiency check。 | 先证明数据足够，再做 UI。 |
| `P0-1` | 定义长程 Agent state protocol v0。 | 把启动、过程、结局的状态协议稳定下来。 |
| `P0-2` | 收敛 interaction pattern catalog。 | 把杂散经验变成部门可理解的高优先级范式。 |
| `P0-3` | 建设三 lane 前端故事线。 | 展示主控、旁路、产品能力并发和 human gate 影响。 |
| `P0-4` | 设计 rollback packet 和 commit-todo-state linkage。 | 让长程任务能撤回、补偿、继续。 |
| `P0-5` | 设计 global manager commands。 | 让用户像管理者一样查看全局进展、gate、风险和 agent 状态。 |
| `P0-6` | 产出部门级 review artifact。 | 把协议、证据、前端 demo、上线清单收敛成可汇报材料。 |

推进顺序应该严格先做准备工作，再做前端。最容易走偏的是先做漂亮页面，最后发现历史状态无法支撑故事。

## 9. 对部门汇报的一句话版本

LoopX 要解决的不是“让 agent 自动多干点活”，而是给长程 Agent
建立一套可继承、可管理、可回滚的状态协议：启动时能接入和生成候选，过程中能按 todo/gate/quota/evidence 推进，结束时能验收、交接或撤回；用户不再是被动回答问题的人，而是管理多条 agent lane 的负责人。
