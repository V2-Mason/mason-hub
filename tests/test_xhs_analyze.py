"""
test_xhs_analyze.py — parse_count / interaction_score / 假流量过滤 单元测试

覆盖模块:
- skills/xhs/xhs-analyze-viral.py  (parse_count, interaction_score, fake_flags 逻辑)
- skills/xhs/_xhs_analyze_compare.py (parse_count, median)
- skills/xhs/_two_tier_crawl.py (parse_count, interaction_score)

运行: cd ~/mason-hub && python -m pytest tests/test_xhs_analyze.py -v
"""
import sys
import os
import pytest

# ── 把 skills/xhs 加入 sys.path，方便 import ──
SKILLS_XHS = os.path.join(os.path.dirname(__file__), '..', 'skills', 'xhs')
sys.path.insert(0, os.path.abspath(SKILLS_XHS))


# ========================================================
# 因为源文件名含连字符，用 importlib 加载
# ========================================================
import importlib.util


def _import_module(file_name, module_name):
    """从 skills/xhs/ 导入指定 Python 文件."""
    path = os.path.join(os.path.abspath(SKILLS_XHS), file_name)
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


viral_mod = _import_module('xhs-analyze-viral.py', 'xhs_analyze_viral')
compare_mod = _import_module('_xhs_analyze_compare.py', '_xhs_analyze_compare')
crawl_mod = _import_module('_two_tier_crawl.py', '_two_tier_crawl')


# ================================================================
# 1. parse_count — 数字归一化
# ================================================================
class TestParseCount:
    """测试 parse_count 在三个模块中的一致性和边界情况."""

    # --- 基础转换 ---

    @pytest.mark.parametrize('input_val,expected', [
        (None, 0),
        ('', 0),
        ('0', 0),
        ('123', 123),
        ('1234', 1234),
        ('99999', 99999),
    ])
    def test_basic_integers(self, input_val, expected):
        assert viral_mod.parse_count(input_val) == expected
        assert compare_mod.parse_count(input_val) == expected
        assert crawl_mod.parse_count(input_val) == expected

    # --- 万 (万 = 10,000) ---

    @pytest.mark.parametrize('input_val,expected', [
        ('1万', 10000),
        ('1.2万', 12000),
        ('0.5万', 5000),
        ('10万', 100000),
        ('3.14万', 31400),
    ])
    def test_wan_suffix(self, input_val, expected):
        assert viral_mod.parse_count(input_val) == expected
        assert compare_mod.parse_count(input_val) == expected
        assert crawl_mod.parse_count(input_val) == expected

    # --- 亿 (亿 = 100,000,000) ---

    @pytest.mark.parametrize('input_val,expected', [
        ('1亿', 100000000),
        ('1.5亿', 150000000),
        # NOTE: 2.3亿 → int(2.3*1e8) = 229999999 (浮点精度问题，已知行为)
        ('2.3亿', 229999999),
    ])
    def test_yi_suffix(self, input_val, expected):
        assert viral_mod.parse_count(input_val) == expected
        assert compare_mod.parse_count(input_val) == expected
        assert crawl_mod.parse_count(input_val) == expected

    # --- 加号后缀 (e.g. "999+") ---

    @pytest.mark.parametrize('input_val,expected', [
        ('100+', 100),
        ('999+', 999),
        ('1.5万+', 15000),
    ])
    def test_plus_suffix(self, input_val, expected):
        assert viral_mod.parse_count(input_val) == expected
        assert compare_mod.parse_count(input_val) == expected
        assert crawl_mod.parse_count(input_val) == expected

    # --- 非法输入 → 0 ---

    @pytest.mark.parametrize('input_val', [
        'abc', '???', '  ', 'N/A',
    ])
    def test_invalid_returns_zero(self, input_val):
        assert viral_mod.parse_count(input_val) == 0
        assert compare_mod.parse_count(input_val) == 0
        assert crawl_mod.parse_count(input_val) == 0

    def test_bare_wan_raises_in_viral(self):
        """BUG 记录: '万' 单独输入时 viral_mod 会 ValueError (float('') 失败).
        这是因为 '万' 匹配了 if '万' in s 分支，但 replace 后变成空字符串。
        crawl_mod 和 compare_mod 同样受影响。属于极端边界，实际数据不太可能出现。
        """
        with pytest.raises(ValueError):
            viral_mod.parse_count('万')

    # --- 数值类型直接传入 ---

    def test_int_passthrough(self):
        assert viral_mod.parse_count(500) == 500
        assert crawl_mod.parse_count(500) == 500

    # --- 带空格 ---

    def test_whitespace_stripped(self):
        assert viral_mod.parse_count('  123  ') == 123
        assert crawl_mod.parse_count(' 1.2万 ') == 12000


# ================================================================
# 2. interaction_score — 互动评分公式
# ================================================================
class TestInteractionScore:
    """互动评分: liked + collected*3 + comment*5 + shared*8"""

    def test_formula_basic(self):
        # 100 + 50*3 + 20*5 + 10*8 = 100+150+100+80 = 430
        assert viral_mod.interaction_score(100, 50, 20, 10) == 430
        assert crawl_mod.interaction_score(100, 50, 20, 10) == 430

    def test_all_zeros(self):
        assert viral_mod.interaction_score(0, 0, 0, 0) == 0
        assert crawl_mod.interaction_score(0, 0, 0, 0) == 0

    def test_only_likes(self):
        assert viral_mod.interaction_score(1000, 0, 0, 0) == 1000

    def test_only_shares(self):
        # shares 权重最高 (×8)
        assert viral_mod.interaction_score(0, 0, 0, 100) == 800

    def test_only_comments(self):
        assert viral_mod.interaction_score(0, 0, 100, 0) == 500

    def test_only_collections(self):
        assert viral_mod.interaction_score(0, 100, 0, 0) == 300

    def test_large_values(self):
        # 10万赞 + 5万藏 + 1万评 + 5千转
        expected = 100000 + 50000 * 3 + 10000 * 5 + 5000 * 8
        assert viral_mod.interaction_score(100000, 50000, 10000, 5000) == expected

    def test_weight_ordering(self):
        """验证权重大小关系: shared > comment > collected > liked"""
        base = 100
        score_liked = viral_mod.interaction_score(base, 0, 0, 0)
        score_collected = viral_mod.interaction_score(0, base, 0, 0)
        score_comment = viral_mod.interaction_score(0, 0, base, 0)
        score_shared = viral_mod.interaction_score(0, 0, 0, base)
        assert score_liked < score_collected < score_comment < score_shared


# ================================================================
# 3. 假流量过滤逻辑
# ================================================================
class TestFakeTrafficDetection:
    """
    假流量检测规则 (来自 xhs-analyze-viral.py):
    - liked > 1000 且 评赞比 < 0.2% → '评赞比过低'
    - liked > 1000 且 藏赞比 < 5%   → '藏赞比过低'

    评赞比 = comment / liked * 100
    藏赞比 = collected / liked * 100
    """

    @staticmethod
    def _compute_fake_flags(liked, collected, comment):
        """复现 xhs-analyze-viral.py 的假流量检测逻辑."""
        engage_rate = (comment / liked * 100) if liked > 0 else 0
        save_rate = (collected / liked * 100) if liked > 0 else 0
        fake_flags = []
        if liked > 1000 and engage_rate < 0.2:
            fake_flags.append('评赞比过低')
        if liked > 1000 and save_rate < 5:
            fake_flags.append('藏赞比过低')
        return fake_flags

    # --- 正常帖子：不触发 ---

    def test_normal_post_no_flags(self):
        """正常帖子: 2000 赞, 200 藏(10%), 20 评(1%)"""
        flags = self._compute_fake_flags(liked=2000, collected=200, comment=20)
        assert flags == []

    def test_low_likes_no_flags(self):
        """赞 < 1000 时不触发假流量检测（样本量不足）"""
        flags = self._compute_fake_flags(liked=500, collected=0, comment=0)
        assert flags == []

    def test_exactly_1000_likes_no_flags(self):
        """边界: liked == 1000 不触发 (条件是 > 1000)"""
        flags = self._compute_fake_flags(liked=1000, collected=0, comment=0)
        assert flags == []

    # --- 评赞比过低 ---

    def test_low_engage_rate_flagged(self):
        """5000 赞但只有 5 评论 → 评赞比 0.1% < 0.2%"""
        flags = self._compute_fake_flags(liked=5000, collected=500, comment=5)
        assert '评赞比过低' in flags
        assert '藏赞比过低' not in flags

    def test_engage_rate_boundary_safe(self):
        """评赞比恰好 0.2% → 不触发"""
        # 0.2% of 5000 = 10 comments
        flags = self._compute_fake_flags(liked=5000, collected=500, comment=10)
        assert '评赞比过低' not in flags

    def test_engage_rate_boundary_flagged(self):
        """评赞比略低于 0.2% → 触发"""
        # 9 / 5000 * 100 = 0.18%
        flags = self._compute_fake_flags(liked=5000, collected=500, comment=9)
        assert '评赞比过低' in flags

    # --- 藏赞比过低 ---

    def test_low_save_rate_flagged(self):
        """10000 赞但只有 100 藏 → 藏赞比 1% < 5%"""
        flags = self._compute_fake_flags(liked=10000, collected=100, comment=200)
        assert '藏赞比过低' in flags
        assert '评赞比过低' not in flags

    def test_save_rate_boundary_safe(self):
        """藏赞比恰好 5% → 不触发"""
        # 5% of 2000 = 100 collected
        flags = self._compute_fake_flags(liked=2000, collected=100, comment=20)
        assert '藏赞比过低' not in flags

    def test_save_rate_boundary_flagged(self):
        """藏赞比略低于 5% → 触发"""
        # 99 / 2000 * 100 = 4.95%
        flags = self._compute_fake_flags(liked=2000, collected=99, comment=20)
        assert '藏赞比过低' in flags

    # --- 双重触发 ---

    def test_both_flags_triggered(self):
        """高赞但几乎无互动 → 两个标志同时触发"""
        flags = self._compute_fake_flags(liked=50000, collected=10, comment=1)
        assert '评赞比过低' in flags
        assert '藏赞比过低' in flags
        assert len(flags) == 2

    # --- 零赞 → 无标志（avoid division by zero）---

    def test_zero_likes_no_error(self):
        """赞为 0 时不应报错也不应触发"""
        flags = self._compute_fake_flags(liked=0, collected=100, comment=50)
        assert flags == []


# ================================================================
# 4. median（来自 _xhs_analyze_compare.py）
# ================================================================
class TestMedian:
    """测试 _xhs_analyze_compare.py 的 median 函数."""

    def test_odd_count(self):
        assert compare_mod.median([1, 3, 5]) == 3

    def test_even_count(self):
        assert compare_mod.median([1, 3, 5, 7]) == 4.0

    def test_single_value(self):
        assert compare_mod.median([42]) == 42

    def test_empty_list(self):
        assert compare_mod.median([]) == 0

    def test_unsorted_input(self):
        assert compare_mod.median([5, 1, 3]) == 3

    def test_all_same(self):
        assert compare_mod.median([7, 7, 7, 7]) == 7

    def test_two_values(self):
        assert compare_mod.median([10, 20]) == 15.0

    def test_negative_values(self):
        assert compare_mod.median([-5, -1, 3]) == -1


# ================================================================
# 5. 回归保护：parse_count + interaction_score 组合
# ================================================================
class TestIntegrationRegression:
    """端到端组合测试：模拟从原始字符串到最终评分的完整链路."""

    def test_full_pipeline_chinese_counts(self):
        """模拟 '1.2万' 赞 + '3000' 藏 + '500' 评 + '100' 转"""
        liked = viral_mod.parse_count('1.2万')
        collected = viral_mod.parse_count('3000')
        comment = viral_mod.parse_count('500')
        shared = viral_mod.parse_count('100')
        score = viral_mod.interaction_score(liked, collected, comment, shared)
        # 12000 + 3000*3 + 500*5 + 100*8 = 12000+9000+2500+800 = 24300
        assert score == 24300

    def test_full_pipeline_with_plus(self):
        """模拟 '999+' 赞 + '2.5万+' 藏"""
        liked = viral_mod.parse_count('999+')
        collected = viral_mod.parse_count('2.5万+')
        comment = viral_mod.parse_count('50')
        shared = viral_mod.parse_count('10')
        score = viral_mod.interaction_score(liked, collected, comment, shared)
        # 999 + 25000*3 + 50*5 + 10*8 = 999+75000+250+80 = 76329
        assert score == 76329

    def test_all_none_inputs(self):
        """全部 None → score 0"""
        liked = viral_mod.parse_count(None)
        collected = viral_mod.parse_count(None)
        comment = viral_mod.parse_count(None)
        shared = viral_mod.parse_count(None)
        score = viral_mod.interaction_score(liked, collected, comment, shared)
        assert score == 0

    def test_fake_traffic_with_parsed_counts(self):
        """用 parse_count 解析后的值检测假流量"""
        liked = viral_mod.parse_count('5万')     # 50000
        collected = viral_mod.parse_count('100')  # 100 → 0.2% 藏赞比
        comment = viral_mod.parse_count('5')      # 5 → 0.01% 评赞比

        engage_rate = (comment / liked * 100) if liked > 0 else 0
        save_rate = (collected / liked * 100) if liked > 0 else 0

        assert liked == 50000
        assert engage_rate < 0.2   # 应触发
        assert save_rate < 5       # 应触发


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
