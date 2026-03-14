#!/bin/bash
# test_account_isolation.sh — 验证多 account 上下文隔离
#
# 测试原理：模拟 run-agent.sh 的注入逻辑，检查不同 TASK_ACCOUNT 下
# 只加载对应 account 的文件，不泄露其他 account 数据。

HUB_DIR="$HOME/mason-hub"
PASS=0
FAIL=0

assert_contains() {
  local label="$1" haystack="$2" needle="$3"
  if echo "$haystack" | grep -q "$needle"; then
    echo "  ✅ $label"
    PASS=$((PASS + 1))
  else
    echo "  ❌ $label — 未找到 '$needle'"
    FAIL=$((FAIL + 1))
  fi
}

assert_not_contains() {
  local label="$1" haystack="$2" needle="$3"
  if echo "$haystack" | grep -q "$needle"; then
    echo "  ❌ $label — 不应包含 '$needle' 但找到了（泄露！）"
    FAIL=$((FAIL + 1))
  else
    echo "  ✅ $label"
    PASS=$((PASS + 1))
  fi
}

# 模拟注入：读取 account 文件
load_account_context() {
  local account="$1"
  local agent="$2"
  local account_dir="$HUB_DIR/accounts/$account"
  local result=""

  if [ -d "$account_dir" ]; then
    [ -f "$account_dir/shared.md" ] && result="$result$(cat "$account_dir/shared.md")"
    [ -f "$account_dir/memory/${agent}.md" ] && result="$result$(cat "$account_dir/memory/${agent}.md")"
    [ -f "$account_dir/context/brief.md" ] && result="$result$(head -c 3000 "$account_dir/context/brief.md")"
  fi
  echo "$result"
}

echo "=== Account 隔离测试 ==="

# Test 1: _test account 加载正确内容
echo ""
echo "Test 1: _test account 加载自己的内容"
ctx=$(load_account_context "_test" "EMP_0002")
assert_contains "Pipe 2 shared.md 存在" "$ctx" "TEST_MARKER"
assert_contains "Pipe 3 EMP_0002.md 存在" "$ctx" "TEST_PIPE3"
assert_contains "Brief 存在" "$ctx" "TEST_ISOLATION_CHECK"

# Test 2: _test account 不包含 surenxuan 数据
echo ""
echo "Test 2: _test account 不泄露 surenxuan 数据"
assert_not_contains "无素仁轩品牌信息" "$ctx" "韩国本土直采"
assert_not_contains "无素仁轩产品信息" "$ctx" "COSRX"
assert_not_contains "无素仁轩渠道信息" "$ctx" "三号矩阵"

# Test 3: surenxuan account 加载正确内容
echo ""
echo "Test 3: surenxuan account 加载自己的内容"
ctx_srx=$(load_account_context "surenxuan" "EMP_0001")
assert_contains "Pipe 2 品牌核心" "$ctx_srx" "韩国本土直采"
assert_contains "Pipe 3 选品经验" "$ctx_srx" "实际活跃 SKU"

# Test 4: surenxuan account 不包含 _test 数据
echo ""
echo "Test 4: surenxuan account 不泄露 _test 数据"
assert_not_contains "无 test marker" "$ctx_srx" "TEST_MARKER"
assert_not_contains "无 test pipe3" "$ctx_srx" "TEST_PIPE3"

# Test 5: 无 account 时不注入任何 account 内容
echo ""
echo "Test 5: 无 TASK_ACCOUNT 时不注入"
ctx_none=$(load_account_context "" "EMP_0002")
assert_not_contains "无 test 内容" "$ctx_none" "TEST_MARKER"
assert_not_contains "无素仁轩内容" "$ctx_none" "韩国本土直采"

echo ""
echo "=== 结果: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
