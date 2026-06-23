# 部门汇报：长程 Agent 的状态协议与管理面

LoopX 的部门级叙事不应停在“自动续航”或“todo 列表”。它更重要的价值是：把长程任务中原本散落在聊天、PR、active state、dashboard、quota 和人的判断里的信息，整理成一套可继承、可展示、可回滚的状态协议。

这份文档基于仓库当前实现和最近自迭代积累，回答五个问题：

1. 长程 Agent 从启动、运行到收尾，哪些状态必须成为协议。
2. 哪些状态是源事实，哪些只是 projection 后给用户或前端看的展示协议。
3. LoopX 已经实现了哪些，哪些仍只是设计或弱约束。
4. 长程任务流转有哪些可复用范式，包括 Human in the loop。
5. 如何把主控、旁路、产品能力三条 agent lane 的自迭代历史，补成可信的部门演示和前端动画。

## 1. 当前进展与计划变化

这份文档本身就是当前 P0 队列的工作台。后续推进时，计划变化和已完成准备工作都先写在这里，再同步到 LoopX todo 状态。

| 时间 | 进展 | 影响 |
| --- | --- | --- |
| 2026-06-23 | 已完成 `P0-prep-1`，PR #602 合入。 | `loopx_rollout_event_v0` 增加 lane、state transition、causality、handoff、code refs 等可选字段，为三 agent 动画打基础。 |
| 2026-06-23 | 本轮根据用户反馈重写部门协议文档。 | 把状态定义拆成源事实协议和展示投影协议；把范式扩展到 14 个；补充历史动画的推断补齐策略。 |
| 下一步 | 推进 `P0-prep-2`。 | 生成 public-safe 三 agent 自迭代 fixture，用现有历史加可审计推断补齐主控、旁路、产品能力三条 lane。 |

当前最重要的产品目标可以压缩成一句话：

> 新项目 5 分钟内接入 LoopX，列出若干候选 todo，用户接受后即进入可持续 loop；过程中用户像管理者一样看 gate、进展、风险和结果，而不是盯着单个 agent 聊天窗口。

## 2. 状态协议分层

LoopX 的状态必须分两层讲清楚，否则部门汇报会混淆“事实在哪里”和“界面看到什么”。

### 2.1 源事实协议

源事实协议是写入型状态，是 agent、CLI、主控线程继续工作的依据。它们不能被 dashboard 或展示层反向编辑。

| 协议 | 代码或文档对应 | 已实现程度 | 说明 |
| --- | --- | --- | --- |
| `goal_identity` | registry、active state、[`docs/agent-profile-contract.md`](../agent-profile-contract.md) | 已实现但分散 | 记录 `goal_id`、项目路径、主控/旁路 agent、scope、工作区策略。 |
| `connection_state` | `loopx connect`、`loopx bootstrap`、doctor、[`README.md`](../../README.md) | 已实现 | 区分复用已有连接、只读接入、初始化 goal、本地状态缺失等情况。 |
| `local_state_boundary` | `.gitignore`、doctor、getting-started 文档 | 已实现 | `.loopx/`、`.codex/goals/`、`.local/` 等本地状态不得进入公开提交。 |
| `todo_item_v0` | [`loopx/status.py`](../../loopx/status.py)、[`loopx/cli_commands/todo.py`](../../loopx/cli_commands/todo.py)、[`docs/project-agent-todo-contract.md`](../project-agent-todo-contract.md) | 已实现 | 记录正式工作单元，包含 status、role、task_class、action_kind、claimed_by、resume_when、unblocks_todo_id 等字段。 |
| `interaction_contract_v0` | [`loopx/quota.py`](../../loopx/quota.py)、[`docs/quota-allocation.md`](../quota-allocation.md) | 已实现 | 每次 heartbeat 前判断 user_channel、agent_channel、cli_channel，决定通知、推进、安静和 spend。 |
| `work_lane_contract_v1` | [`loopx/quota.py`](../../loopx/quota.py) | 已实现 | 区分 advancement_task 与 continuous_monitor，给 agent 一个本轮应该执行的 lane contract。 |
| `agent_lane_next_action_v0` | [`loopx/quota.py`](../../loopx/quota.py)、[`docs/project-agent-todo-contract.md`](../project-agent-todo-contract.md) | 已实现 | 面向具体 agent 排出当前可执行 todo，保留 goal-level next action，不覆盖主控视角。 |
| `loopx_rollout_event_v0` | [`loopx/rollout_event_log.py`](../../loopx/rollout_event_log.py) | 已实现，字段刚补强 | 记录 todo、quota、validation、PR、refresh、failure、benchmark 等 public-safe 事件。 |
| `run_history` | `refresh-state`、status builder、quota 记录 | 已实现 | 记录 recent run 的 classification、recommended_action、health 等信息，是当前 projection 的主要来源之一。 |
| `content_ops_surface_v0` | [`loopx/content_ops_surface.py`](../../loopx/content_ops_surface.py) | 已实现 | 覆盖公开社媒、私聊 connector gate、素材、角度、草稿、反馈、发布 gate。 |
| `issue_fix_intake_v0` / `issue_fix_acceptance_loop_v0` | [`loopx/issue_fix_intake_surface.py`](../../loopx/issue_fix_intake_surface.py)、[`loopx/issue_fix_acceptance_loop.py`](../../loopx/issue_fix_acceptance_loop.py) | 已实现 | 支持 repo issue metadata intake、fix artifact、acceptance loop。 |
| `ml_experiment_*` | [`loopx/ml_experiment.py`](../../loopx/ml_experiment.py) | 已实现 | 支持实验场景的 domain pack、dataset window、hypothesis ledger、result 和 replan。 |
| `todo_suggestion_prompt_v0` | [`loopx/todo_suggestion_prompt.py`](../../loopx/todo_suggestion_prompt.py) | 已实现为 prompt packet | 引导用户的 agent 生成候选 todo，但不自动写正式 backlog。 |
| `rollback_packet_v0` | 本文档第 7 节 | 未实现 | 需要把 todo、commit、event、decision、validation 串成可撤回的补偿动作。 |

### 2.2 展示投影协议

展示投影协议是只读视图。它服务用户、agent 和前端理解状态，但不拥有写权限。

| Projection | 代码或文档对应 | 已实现程度 | 展示用途 |
| --- | --- | --- | --- |
| `status_contract_v2` | [`loopx/status.py`](../../loopx/status.py)、[`docs/status-data-contract.md`](../status-data-contract.md) | 已实现 | dashboard 和 CLI status 的总入口。 |
| `goal_channel_projection_v0` | [`loopx/frontstage.py`](../../loopx/frontstage.py) | 已实现 | 给用户/agent 看 waiting_on、latest_status、next_action、user_todos、agent_todos、open_gates、active_leases、recent_events。 |
| `todo_index_v0` | [`loopx/status.py`](../../loopx/status.py) | 已实现 | 把 attention queue 和 rollout todo events 汇总成最多 240 个 todo 索引项。 |
| `todo_projection_view_v0` | [`loopx/status.py`](../../loopx/status.py) | 已实现 | 用于项目资产 todo 投影和 projection gap 检查。 |
| `issue_meta_surface_v0` | [`loopx/status.py`](../../loopx/status.py) | 已实现 | 从 active state 中投影 issue/PR metadata surface。 |
| `task_graph_projection_v0` | [`docs/reference/protocols/task-graph-projection-v0.md`](../reference/protocols/task-graph-projection-v0.md) | 文档已有，落地不足 | 可表达 blocks、validates、handoff、supersedes、rollback 等图关系。 |
| `frontstage dashboard` | [`apps/dashboard/src/views/frontstage-page.tsx`](../../apps/dashboard/src/views/frontstage-page.tsx) | 已有基础 | 已能展示 ops mode、goal_channel_projection、demo fixture fallback。 |
| `rollout_event_summary_v0` | [`loopx/rollout_event_log.py`](../../loopx/rollout_event_log.py) | 已实现 | 可汇总 event kind、agent、todo、classification，但还未充分进入前端故事线。 |
| `department_animation_fixture_v0` | 本文档第 6 节 | 待建设 | 面向部门汇报和前端动画的 public-safe 推断 fixture。 |

### 2.3 已对齐的实现

这些点已经可以在代码里找到明确支撑：

1. `goal_channel_projection_v0` 明确是 read-only projection，`truth_contract` 也声明 projection 不可写。
2. `interaction_contract_v0` 已经把 user、agent、CLI 三个 channel 拆开，能表达“无需通知但必须推进”的状态。
3. `agent_lane_next_action_v0` 已支持按 agent 选择当前 todo，避免旁路 agent 覆盖全局 next action。
4. todo CLI 已支持 `claim`、`update`、`complete`、`supersede`、`deferred`、`resume_when`、`unblocks_todo_id`、`suggest`。
5. `loopx_rollout_event_v0` 已能记录 event kind、agent、todo、classification、artifact refs，并已补入 lane、state transition、causality、handoff、code refs。
6. issue fix、自媒体运营、ML experiment 三类场景已有各自状态面，不再只是概念。
7. dashboard 已有 goal projection 渲染入口，具备接入真实 ops 数据的基础。

### 2.4 仍未对齐或弱约束的部分

这些点需要在部门汇报中如实说明，也要成为下一步 P0 todo 的来源：

1. `rollback_packet_v0` 还没有代码实现；目前只能依赖 commit、PR、todo evidence 的约定。
2. `goal_channel_projection_v0.recent_events` 仍偏短窗口和 run history 视角，尚未充分消费 rollout event 的 before/after、因果、lane、handoff 字段。
3. `task_graph_projection_v0` 有文档，但还不是 dashboard 的稳定输入。
4. 历史 human gate 影响没有被持续结构化保存；当前 open gate 容易展示，已关闭 gate 对路线的影响需要从 todo、event、PR、用户消息中推断。
5. commit 与 todo 的绑定还不是强 schema；目前主要靠 PR body、commit message、todo evidence 和 rollout event refs。
6. `todo suggest` 生成的是提示包，不是自动 repo analyzer；“候选 todo”仍需要用户的 agent 按 prompt 分析后写回。
7. global manager slash commands 还只是产品设计，尚未有 CLI/host integration。
8. 三 agent 自迭代动画需要 public-safe fixture；直接重放历史会缺少旧事件的 state transition 和 causality。

## 3. 全流程状态协议

部门汇报里可以把长程 Agent 生命周期讲成三段：启动、过程、结局。

### 3.1 启动

启动阶段要回答：这个项目是谁的，目标是什么，能不能接入，接入后先做什么。

| 状态 | 源事实 | Projection | 产品要求 |
| --- | --- | --- | --- |
| 项目连接 | registry、project-local `.loopx/registry.json`、active state | status / doctor output | 复用已有连接，不覆盖主控状态。 |
| 目标身份 | `goal_id`、primary agent、side-agent scopes | dashboard 顶部 goal card | 让后续 agent 能知道自己属于哪条 lane。 |
| 本地边界 | `.gitignore`、doctor、check | status warning | 明确本地 LoopX 状态不可提交。 |
| 候选决策 | `todo_suggestion_prompt_v0` 输出、用户选择 | suggested_todos / decision queue | 接入后列出 3 到 5 个候选，不自动塞正式 backlog。 |
| heartbeat | thread automation、`heartbeat-prompt --thin` | next safe action / quota status | 连接后立刻装 heartbeat，但首次长任务应等用户接受候选或已有 runnable todo。 |

启动的理想体验是：用户把当前项目交给 agent，5 分钟内看到 goal id、user gate、top agent todo、下一步安全动作，以及若干可接受的候选 todo。

### 3.2 过程

过程阶段要回答：现在该不该跑，跑哪个 todo，谁负责，能不能越过人类 gate，完成后怎么证明。

| 状态 | 源事实 | Projection | 产品要求 |
| --- | --- | --- | --- |
| 是否运行 | `quota should-run`、`interaction_contract_v0` | user_channel / agent_channel / cli_channel | 区分“通知用户”和“继续安全工作”。 |
| 工作单元 | `todo_item_v0` | user_todos / agent_todos / todo_index | 每个执行动作都落到 todo 或 blocker。 |
| 所有权 | `claimed_by`、worktree guard、side-agent policy | active_leases / lane card | 多 agent 并发时可追踪、可 handoff。 |
| Human gate | user todo、decision scope、open gate | gate card / timeline node | 人的判断必须知道阻塞什么、释放什么。 |
| 证据 | validation result、artifact refs、source refs | evidence list / rollout timeline | 只展示 public-safe 指针，不泄露私密材料。 |
| 额度 | quota spend / void / monitor policy | budget badge / quiet reason | validated writeback 后再 spend。 |
| 修复 | self-repair delta、projection gap、no-progress streak | warning / repair lane | recurring mistake 进入产品或流程改进，不只靠提示词。 |

过程协议的判断顺序应固定：

1. 是否存在具体 user gate。
2. 是否存在 in-scope runnable todo。
3. 当前 agent 是否有 claim 或是否需要 claim。
4. 本轮是否能形成可验证产物。
5. 写回状态后是否应 spend quota。

### 3.3 结局

结局阶段要回答：任务是完成、暂停、失败、转交，还是进入下一轮。

| 状态 | 源事实 | Projection | 产品要求 |
| --- | --- | --- | --- |
| 结果层级 | `delivery_outcome`、validation、PR/commit refs | outcome badge | 区分 surface-only、outcome_progress、primary_goal_outcome。 |
| 后继工作 | successor todo、resume_when、unblocks_todo_id | next action / dependency edge | 下一步不能只留在 prose reason。 |
| 暂停/归档 | no-candidate reason、archive/pause event | quiet state | 安静要有原因。 |
| 发布边界 | publication gate、review todo、PR state | release/readiness panel | 公开 claim 前必须有证据和边界。 |
| 回滚 | `rollback_packet_v0`、commit/todo/event linkage | rollback hint / risk panel | 失败不是擦历史，而是补偿动作。 |

## 4. 长程任务流转的 14 个范式

[`docs/interaction-pattern-catalog.md`](../interaction-pattern-catalog.md) 已经覆盖了很多细节。部门汇报不适合逐条念 catalog，建议收敛成 14 个范式，按优先级表达。

### P0：必须先讲清楚的 8 个范式

1. **有界推进与证据写回**
   每次自动化都是 bounded batch：推进一个 todo、写回一个 blocker、或安静。完成后要 validation、writeback、再 spend。

2. **Human gate 是状态，不是聊天提醒**
   人的判断要有 `decision_scope`、阻塞对象、释放对象、拒绝后的 fallback。用户不是被动答题者，而是管理者。

3. **正式 todo 与候选 todo 分离**
   接入后可生成候选，但不能自动把候选变成 backlog。只有用户或主控 promote 后，才进入正式 todo 生命周期。

4. **多 agent lane 与 claim 所有权**
   主控、旁路、产品能力可以并发，但必须通过 `claimed_by`、worktree、handoff、review todo 和 rollout event 形成可审计关系。

5. **User channel 与 agent channel 分离**
   `interaction_contract_v0` 要区分“需要通知用户”和“agent 仍可继续安全推进”，避免把 owner gate 误读成全局停工。

6. **P0 阻塞时做安全 fallback**
   P0 被 gate 阻塞时，CLI contract 允许的 P1/P2 验证、文档、fixture、projection 修复仍可继续。

7. **公共/私密边界先于执行**
   repo issue、公开社媒、私聊、实验数据都必须先形成 source boundary 和 gate，再决定是否进入 agent todo。

8. **结果层级要高于过程热闹**
   用户看重验收。LoopX 不能只展示漂亮 packet，要最终能把 issue fix、PR、smoke、release note 或可见产物串起来。

### P1：稳定长程运行的 4 个范式

9. **Deferred 与 resume_when 可唤醒**
   “等 CLI 重构后继续”不能只藏在 prose 里，必须能通过 `resume_when`、`unblocks_todo_id` 被候选排序重新发现。

10. **No-candidate 与 projection gap 分离**
    “真的没有候选”要安静；“deferred 已 ready 但没投影”要修复；“有候选但 scope 不匹配”要 handoff。

11. **外部信号先进状态面，再进执行面**
    issue、PR、X、微信、实验结果先变成 readable metadata、gate、candidate、safe action；不是一读到信号就执行。

12. **自修复要沉淀为协议或 smoke**
    反复出错不能只改 prompt。要改 active-state projection、CLI contract、interaction catalog、或 durable smoke。

### P2：形成管理产品感的 2 个范式

13. **Manager summary 是全局读模型**
    用户可以问“最近一天进展”“当前 gate”“哪些 agent 卡住”，系统从 registry、todo、run、quota、rollout 汇总，不要求用户逐线程追问。

14. **Rollback 是补偿式继续，不是删除历史**
    长程任务的撤回要追加 rollback packet、successor todo 和 validation plan，让后续 agent 能继续理解路线变化。

这 14 个范式与 catalog 的关系是：catalog 保留工程细节，部门汇报只讲这些可被产品、工程和管理者共同理解的主干。

## 5. 前端展示方案

前端展示的核心不是“状态卡片多”，而是让用户看到长程任务如何被管理。部门 demo 应围绕一次自迭代故事线：

1. 顶部：goal、当前状态、最近 24 小时进展、当前 user gate、下一安全动作。
2. 中部：三条 agent lane，分别展示主控、旁路、产品能力的 claimed todo、状态变化、最近证据。
3. 中部叠加：human gate 作为 timeline 节点，显示它阻塞了什么、释放了什么、改变了什么。
4. 右侧：rollback 和风险面板，显示可撤回的 commit、todo、event、decision 关系。
5. 底部：rollout timeline，按事件展示 todo add、claim、complete、quota、validation、merge、repair。

### 5.1 当前历史状态能做什么

当前历史状态足够做“实时控制台”：

- `goal_channel_projection_v0` 能展示 top agent todo、user todo、active claim、open gate、recent events。
- `todo_index_v0` 能汇总当前和部分历史 todo。
- rollout event log 已记录 todo、quota、validation、PR、refresh 等事件。
- dashboard 已有 frontstage ops mode 和 projection 渲染入口。

### 5.2 当前历史状态缺什么

当前历史状态还不足以直接做“可信的三 agent 自迭代动画”：

- 旧 rollout event 缺 before/after、causality、lane、handoff。
- `recent_events` 窗口较短，不能复盘完整故事。
- 已关闭 human gate 对后续路线的影响没有稳定 projection。
- commit 与 todo 的绑定还不够强。
- 多 agent review/self-merge/rollback 关系需要从 PR、todo note、event 和 active state 里组合。

所以前端不应直接假装历史完美，而应生成一个 public-safe 的 inferred fixture。

## 6. 历史动画的推断补齐策略

用户指出“历史的迭代情况也要考虑自己推断来补上”。这件事可以做，但必须把推断和事实分开。

### 6.1 目标

构造 `department_animation_fixture_v0`，用于部门汇报和前端演示。它不是新的源事实，只是从 public-safe 证据生成的展示 fixture。

### 6.2 可用证据

| 证据 | 可推断内容 | 可信度 |
| --- | --- | --- |
| rollout event log | event kind、agent、todo、classification、PR/commit refs | 高 |
| active state / todo metadata | todo status、claimed_by、resume_when、evidence、reason | 高 |
| run history / quota | recommended_action、should_run、quiet/no-op、delivery outcome | 中高 |
| PR / commit history | code route、review/merge/self-merge、rollback candidate | 中高 |
| public docs / smoke | validation、public-safe artifact | 中 |
| 用户聊天中的明确决策 | human gate、priority change、scope correction | 中，需要人工标注来源 |
| 缺失连接段 | timeline bridge、lane handoff、causality | 低，只能作为 dashed inferred edge |

### 6.3 Fixture 字段

建议每个动画事件包含：

| 字段 | 含义 |
| --- | --- |
| `event_id` | fixture 内唯一事件。 |
| `source_event_ids` | 对应 rollout/run/todo/PR/commit 证据。 |
| `lane_id` | `main_control`、`side_bypass`、`product_capability`。 |
| `agent_id` | 具体 agent。 |
| `state_transition` | `from_state`、`to_state`；没有事实时标记 inferred。 |
| `causality` | `caused_by`、`blocks`、`unblocks`、`gate_id`、`decision_id`。 |
| `human_effect` | 人类交互改变了 priority、scope、approval、candidate promotion 还是 correction。 |
| `code_refs` | PR、commit、branch、revert_of。 |
| `evidence_refs` | public-safe 文档、smoke、PR、dashboard artifact。 |
| `confidence` | `observed`、`inferred_high`、`inferred_medium`、`synthetic_bridge`。 |
| `display_hint` | 前端渲染建议：solid edge、dashed edge、gate node、review node、rollback node。 |

### 6.4 推断规则

1. rollout event、todo status、PR/commit 是 observed；前端用实线。
2. todo note 中的 “claimed_by / evidence / side-agent self-merged” 可生成 lane event；前端用实线或半实线。
3. 用户明确要求、批准、纠偏可生成 human gate 或 correction event；前端标明“human decision”。
4. 只有时间顺序但缺少显式因果时，生成 `synthetic_bridge`；前端用虚线，不写成事实。
5. 对旧事件补 before/after 时，必须保留 `inference_reason`，例如 “todo status changed from open to done between event A and PR B”。
6. 不读取或嵌入私密原文；只使用 public-safe summary 和指针。

### 6.5 三条 lane 的叙事骨架

| Lane | 角色 | 动画重点 |
| --- | --- | --- |
| `main_control` | 目标路由、review/merge、最终收口 | 从 user goal 到 P0 队列，从 review todo 到 PR merge，从 gate 到下一轮。 |
| `side_bypass` | 独立实现或验证 slice | 展示 claim、独立 worktree、small PR、自合并或交主控 review。 |
| `product_capability` | 场景分析、协议抽象、前端/管理面 | 展示从用户产品反馈到 doc/protocol/todo，再到代码或 fixture 的闭环。 |

`P0-prep-2` 的验收标准是：生成一个 fixture，至少覆盖三条 lane、一个 human gate、一个 handoff/review、一个 validation、一个 PR/commit evidence、一个 inferred dashed edge。

## 7. 长程任务可回滚能力

用户提到“也许得通过 commit - todo 解决”。这是主线，但不够完整。长程任务的回滚至少有五层。

| 层 | 回滚对象 | 推荐方式 |
| --- | --- | --- |
| 代码层 | commit、PR、branch | 用 git revert 或修复 commit，并把 rollback 与 todo/event 关联。 |
| 控制面层 | todo、claim、active state | 不删除历史，追加 supersede、correction、restore checkpoint。 |
| 证据层 | run、validation、benchmark 结论 | 标记 invalidated/superseded，保留 public-safe summary。 |
| 决策层 | user reward、approval、priority | 追加新的 decision/correction overlay。 |
| 展示层 | dashboard、showcase、公开 claim | 更新 publication gate 和 rollback notice。 |

建议新增 `rollback_packet_v0`：

| 字段 | 说明 |
| --- | --- |
| `rollback_id` | 回滚动作身份。 |
| `goal_id` | 所属长程目标。 |
| `todo_ids` | 受影响 todo。 |
| `event_ids` | 受影响 rollout/run events。 |
| `commit_refs` | 需要 revert 或补偿的 commit/PR。 |
| `decision_ids` | 相关人类决策。 |
| `reason` | 为什么撤回。 |
| `safety_class` | 是否需要 human approval。 |
| `proposed_action` | revert、follow-up fix、state correction、doc correction 等。 |
| `validation_plan` | 回滚后如何证明状态恢复。 |
| `successor_todo` | 回滚本身也应该产生下一步。 |

原则是：回滚不是擦掉历史，而是让错误、撤回和路线变化也能进入可继承状态。

## 8. 用户作为管理者的命令面

用户不应该只能逐个线程问“你现在干到哪了”。LoopX 应该支持管理者视角的全局命令，默认只读，必要时再显式 promote 或 approve。

| 命令 | 读取状态 | 输出 |
| --- | --- | --- |
| `/loop-global-summary 最近一天进展` | registry、status、run history、quota、todo index、rollout events | 最近完成、当前卡点、活跃 agent、下一步建议。 |
| `/loop-global-gates` | open user gates、deferred-ready、decision scopes | 需要用户判断的事项，按阻塞价值排序。 |
| `/loop-global-agents` | agent profile、claimed todos、active leases、latest event、workspace guard | 每个 agent 在干什么、是否健康、是否越界。 |
| `/loop-global-todos --priority P0` | todo index、task class、claim、resume_when | 当前 P0 队列、谁负责、哪个能跑、哪个要等。 |
| `/loop-global-risks 最近一天` | projection warnings、private-boundary warnings、dirty worktree、no-progress、quota anomalies | 管理者应该先看的风险。 |
| `/loop-global-rollout loopx-meta 最近一天` | rollout event log、run history、PR/commit refs | 一条可读 timeline，用于复盘和部门汇报。 |
| `/loop-global-review-packet loopx-meta` | status projection、todo graph、recent outcomes、open gates、evidence refs | 给主控或用户的一页式 review packet。 |
| `/loop-global-promote-candidate <candidate_id>` | suggested_todos、decision queue | 明确把候选提升为正式 todo；必须写 human decision。 |
| `/loop-global-rollback-plan <todo_or_pr>` | rollback packet、PR/commit、todo/event linkage | 只生成回滚计划，不默认执行。 |

这些命令的边界要明确：默认不写状态、不执行任务、不替用户批准 gate。写入类命令必须要求 `--apply` 或明确 user decision。

## 9. P0 推进队列

这次部门汇报规划对应的 todo 都是 P0，但顺序有先后。前三项是准备工作，后六项是正式建设。

| 顺序 | Todo | 当前状态 | 目的 | 验收 |
| --- | --- | --- | --- | --- |
| 1 | `P0-prep-1` 补强 rollout event 字段 | done | 让三 agent todo/gate/status 转换能被重放。 | PR #602 已合入；event 支持 lane、transition、causality、handoff、code refs。 |
| 2 | `P0-prep-2` 生成 public-safe 三 agent fixture | next | 让前端和部门汇报有真实故事，不依赖私密日志。 | fixture 覆盖三 lane、human gate、handoff/review、validation、PR/commit、inferred edge。 |
| 3 | `P0-prep-3` 做 frontstage/status sufficiency check | open | 先证明数据足够，再做 UI。 | smoke 能验证 projection 或 fixture 可渲染 todo flow、human gate、evidence、rollback hint。 |
| 4 | `P0-1` 定义长程 Agent state protocol v0 | in progress | 稳定启动、过程、结局的源事实协议。 | 从本文档提炼成 schema/reference doc。 |
| 5 | `P0-2` 收敛 interaction pattern catalog | in progress | 把杂散经验变成部门可讲的 14 个范式。 | catalog 增加一页式 priority map，或本文档被索引引用。 |
| 6 | `P0-3` 建设三 lane 前端故事线 | open | 展示主控、旁路、产品能力并发和 human gate 影响。 | dashboard 可以加载 fixture 或真实 projection，渲染三 lane timeline。 |
| 7 | `P0-4` 设计 rollback packet 和 commit-todo-state linkage | open | 让长程任务能撤回、补偿、继续。 | `rollback_packet_v0` 文档、fixture 节点、最小 smoke。 |
| 8 | `P0-5` 设计 global manager commands | open | 让用户像管理者一样查看全局进展、gate、风险和 agent 状态。 | 命令 spec 和只读 summary packet。 |
| 9 | `P0-6` 产出部门级 review artifact | open | 把协议、证据、前端 demo、上线清单收敛成可汇报材料。 | 一页式汇报材料加 demo 链路。 |

推进顺序不能倒过来。最容易走偏的是先做漂亮页面，最后发现历史状态无法支撑故事；所以先补 event、fixture、sufficiency check，再进入 UI polish。

## 10. 对部门汇报的一句话版本

LoopX 要解决的不是“让 agent 自动多干一点”，而是给长程 Agent 建一套可继承、可管理、可回滚的状态协议：启动时能接入并产生候选，过程中按 todo、gate、quota、evidence 推进，结束时能验收、交接或撤回；用户从被动回答问题的人，变成管理多条 agent lane 的负责人。
