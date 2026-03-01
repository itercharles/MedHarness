# API-Based Testing Framework

## 概述

这个目录包含基于API的测试，替代了原有的浏览器UI测试。API测试直接测试核心业务逻辑，而不是通过UI交互。

## 为什么选择API测试？

### 与浏览器测试对比

| 特性 | 浏览器测试 (sys/crs) | API测试 (api/) |
|------|---------------------|---------------|
| **速度** | 慢 (10-30秒/测试) | 快 (0.1-1秒/测试) |
| **稳定性** | 低 (UI渲染时序问题) | 高 (无UI依赖) |
| **依赖** | Playwright + Streamlit服务器 | 仅核心Python模块 |
| **调试** | 困难 (需要截图/录像) | 容易 (直接Python调试) |
| **CI/CD时间** | 5-10分钟 | 10-30秒 |
| **维护成本** | 高 (UI变化即失败) | 低 (API稳定) |

### 性能提升

- **10-100倍速度提升**：无需启动Web服务器和浏览器
- **并行执行**：可以安全地并行运行所有API测试
- **更快反馈**：开发时可以快速验证逻辑

## 测试覆盖范围

当前的API测试套件覆盖以下系统需求：

1. **SYS-001**: 对象管理与追踪
   - 查看需求、CR、架构对象
   - 按类型过滤对象
   - 搜索对象内容

2. **SYS-003**: 可视化追溯
   - 追溯矩阵数据
   - 追溯图构建
   - 上下游关系

3. **SYS-004**: 孤立项检测
   - 检测孤立项
   - 孤立项排除规则
   - 孤立项计数

4. **SYS-005**: 合规性评估
   - 加载策略组
   - 查看策略定义
   - 运行合规性检查
   - 合规性评分计算

5. **SYS-008**: 变更管理
   - 列出变更请求
   - 查看CR详情
   - 追踪受影响项
   - 创建和编辑CR
   - 影响分析

6. **SYS-010**: 生命周期工作流
   - 查看生命周期状态
   - 获取可用转换
   - 执行状态转换
   - CR工作流
   - 状态历史追踪

## 如何运行

### 运行所有API测试

```bash
pytest tests/api/ -v
```

### 运行特定模块

```bash
# 对象管理测试
pytest tests/api/test_api_001_object_management.py -v

# 追溯性测试
pytest tests/api/test_api_003_traceability.py -v

# 合规性测试
pytest tests/api/test_api_005_compliance.py -v
```

### 运行单个测试

```bash
pytest tests/api/test_api_001_object_management.py::test_TC_SYS_001_001_view_requirement_object -v
```

### 并行运行（更快）

```bash
pytest tests/api/ -v -n auto
```

## 测试结构

每个测试文件对应一个系统需求（SYS-XXX）：

```
tests/api/
├── __init__.py                          # 包初始化和文档
├── conftest.py                          # 共享fixtures
├── test_api_001_object_management.py    # SYS-001测试
├── test_api_003_traceability.py         # SYS-003测试
├── test_api_004_orphan_detection.py     # SYS-004测试
├── test_api_005_compliance.py           # SYS-005测试
├── test_api_008_change_management.py    # SYS-008测试
└── test_api_010_lifecycle.py            # SYS-010测试
```

## Fixtures

### `test_dhf_root`

创建隔离的临时DHF目录，包含测试数据：

```python
def test_example(test_dhf_root):
    core = CompliantFlowCore(test_dhf_root)
    item = core.get_item("SRS-001")
    assert item is not None
```

测试数据包括：
- UC-001: 用例
- CRS-001: 客户需求
- SYS-001, SYS-002: 系统需求
- SRS-001, SRS-002: 软件需求
- SYSARCH-001: 系统架构
- CR-001: 变更请求
- IEC_62304: 合规性策略组

## 当前状态

✅ **已完成**：
- API测试框架建立
- 31个API测试创建
- Fixture配置
- 测试数据生成

🔨 **进行中**：
- 修复dict/object访问不一致
- 补充missing的test data
- 完善异常场景测试

📝 **待办**：
- 添加性能基准测试
- 添加integration tests
- 考虑删除旧的浏览器测试（保留少数关键UI测试）

## 迁移指南

### 从浏览器测试迁移

**旧的浏览器测试**：
```python
def test_view_requirement(page, streamlit_app):
    page.goto(f"{streamlit_app}/page_SRS?item=SRS-001")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("heading", name="SRS-001")).to_be_visible()
    assert "Item Persistence" in page.content()
```

**新的API测试**：
```python
def test_view_requirement(test_dhf_root):
    core = CompliantFlowCore(test_dhf_root)
    item = core.get_item("SRS-001")
    assert item["id"] == "SRS-001"
    assert "Item Persistence" in item["title"]
```

### 优势对比

- **更快**: 0.1秒 vs 10秒
- **更清晰**: 直接验证数据而非UI元素
- **更稳定**: 无渲染时序问题
- **更易调试**: 可以直接print/pdb调试

## 最佳实践

1. **使用描述性测试名称**：`test_TC_SYS_XXX_YYY_功能描述`
2. **每个测试一个断言场景**：专注单一功能点
3. **使用fixtures隔离数据**：每个测试独立的DHF
4. **清晰的文档字符串**：包含@links和@test_id
5. **快速失败**：早期断言，清晰错误消息

## 贡献指南

添加新的API测试时：

1. 确定要测试的系统需求（SYS-XXX）
2. 创建或更新对应的test_api_XXX.py文件
3. 使用test_dhf_root fixture
4. 包含完整的docstring和metadata
5. 运行测试确保通过
6. 更新本README

## 常见问题

### Q: 为什么有些测试失败？
A: 当前阶段API返回dict而非对象，需要调整断言从`item.id`改为`item["id"]`。

### Q: 如何添加新的测试数据？
A: 修改`tests/fixtures/test_data.py`中的`populate_test_dhf()`函数。

### Q: API测试能完全替代UI测试吗？
A: 不能完全替代。API测试验证业务逻辑，但关键UI交互仍需少量浏览器测试（如图表渲染、用户工作流）。

### Q: 测试速度有多快？
A: 在MacBook Pro上，31个API测试约2-3秒完成（vs 浏览器测试需5-10分钟）。

## 未来规划

1. **完成当前测试修复** - 调整dict访问
2. **添加更多测试场景** - 边界条件、错误处理
3. **性能基准** - 确保API性能
4. **集成测试** - 跨模块交互
5. **逐步移除浏览器测试** - 保留关键UI测试
6. **文档生成测试** - PDF生成验证
7. **Git集成测试** - 版本控制功能

## 联系

如有问题或建议，请创建Issue或PR。
