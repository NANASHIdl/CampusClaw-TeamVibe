---
name: write-tests
description: 按测试规范为一条能力补测试（单元 / 接口 / 组件 / 端到端），含三类组织、断言有效性与数据隔离。当新增接口、修复缺陷、或某条 Scenario 没有对应用例时使用。
---

# 技能：按规范补测试

## 何时用

- 新增或修改接口、业务规则、页面状态；
- 修复缺陷（**先补复现用例**）；
- `docs/lesson-07/02-capability-scenario-matrix.md` 里某条 Scenario 没有对应用例。

## 步骤

1. **找源头**：打开对应 `openspec/changes/<变更名>/specs/<能力>/spec.md`，记下要覆盖的 Scenario 编号（如 `MT-13`）。
2. **定层次**：业务规则 → `backend/tests/unit/`；接口行为 → `backend/tests/api/api/v1/<资源>/test_<方法>.py`；页面状态 → `frontend/src/**/__tests__/*.spec.ts`；主路径 → `e2e/`。
3. **写名字**：函数名 `test_<能力>_<场景>`，docstring 写 `"<编号> <一句话>（依据 docs/specs/xx §y）"`。
4. **归三类**：同一能力至少覆盖正常路径 1 条、失败路径 4 条（参数非法 / 无权限 / 资源不存在 / 依赖不可达）、边界 2 条（等价类两端）。
5. **断言值，不断言形状**：
   - ❌ `assert 200` + `assert is not None` + `assert len == seeded`
   - ✅ 跨班响应体与「不存在」响应体除 `request_id` 外逐字节相同；`citations == []` 且 `answer == "资料中未找到相关内容"`；幂等后查库行数不增。
6. **隔离数据**：用 `campusclaw_test` 库；fixture 事务回滚；预置 A / B 两班；不依赖执行顺序。
7. **替身**：模型与嵌入用 `tests/fakes/`；依赖不可达用「指向不存在端口」制造，不用 monkeypatch 抛异常。
8. **跑门禁**：`make test-api` / `make test-web`，再 `make check`。

## 完成判据

- 每条新增 Scenario 至少一条用例，且**改坏被测逻辑它会红**（手工验证一次：注释掉关键判断，测试应变红，然后恢复）；
- 断网后单元与接口测试全绿；
- 没有新增 `skip`（新增必须带理由与追踪编号）。
