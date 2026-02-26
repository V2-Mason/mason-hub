#!/bin/bash
# Mason HQ 启动脚本
# 用法: ~/mason-hub/scripts/start-hq.sh
# 功能: 自动创建 tmux 3-pane 常驻布局（Meta Manager + SRE + Platform Dev）
#       每个 pane 启动 Claude Code 并自动注入角色指令
#       业务 domain 按需手动添加

SESSION="hq"
PROJECT_DIR="$HOME/mason-hub"

# 如果已有 hq session，先提示
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "⚠️  tmux session 'hq' 已存在"
    echo "   连接:       tmux attach -t hq"
    echo "   销毁后重建: tmux kill-session -t hq && ~/mason-hub/scripts/start-hq.sh"
    exit 1
fi

echo "🚀 启动 Mason HQ..."

# 环境变量
ENV="export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 && export CLAUDE_CODE_AGENT_TEAMS_DISPLAY=split"
LOGGED="$PROJECT_DIR/scripts/claude-logged.sh"

# 创建 session，pane 0: Meta Manager（左上）
tmux new-session -d -s "$SESSION" -c "$PROJECT_DIR" -x 200 -y 50
tmux send-keys -t "$SESSION:0.0" "$ENV && cd $PROJECT_DIR && $LOGGED EMP_0000 'Meta Manager' '读取 agents/EMP_0000.md，你是 Meta Manager。遵守该文件中的所有职责定义和行为边界。启动后说一句简短的状态报告。'" Enter

# 左右分屏，pane 1: Platform Dev（右侧）
tmux split-window -h -t "$SESSION:0.0" -c "$PROJECT_DIR"
tmux send-keys -t "$SESSION:0.1" "$ENV && cd $PROJECT_DIR && $LOGGED EMP_0002 'Platform Dev' '读取 agents/EMP_0002.md，你是 Platform Dev。遵守该文件中的所有职责定义和行为边界。启动后说一句简短的状态报告。'" Enter

# pane 0 上下分屏，pane 2: SRE（左下）
tmux split-window -v -t "$SESSION:0.0" -c "$PROJECT_DIR"
tmux send-keys -t "$SESSION:0.2" "$ENV && cd $PROJECT_DIR && $LOGGED EMP_0004 'SRE Agent' '读取 agents/EMP_0004.md，你是 SRE Agent。遵守该文件中的所有职责定义和行为边界。运行 uptime、df -h、free -h、systemctl status slack-bot，给出简短健康报告。'" Enter

# 等待启动
sleep 3

# 给每个 pane 加标题
tmux select-pane -t "$SESSION:0.0" -T "💼 Meta Manager"
tmux select-pane -t "$SESSION:0.1" -T "⚙️ Platform Dev"
tmux select-pane -t "$SESSION:0.2" -T "🔧 SRE"

# 开启 pane 标题显示
tmux set-option -t "$SESSION" pane-border-status top
tmux set-option -t "$SESSION" pane-border-format " #{pane_title} "

# 回到 pane 0 (Meta Manager)
tmux select-pane -t "$SESSION:0.0"

echo ""
echo "✅ Mason HQ 已启动！（常驻 3 pane）"
echo ""
echo "┌──────────────────────┬──────────────────────┐"
echo "│ 💼 Meta Manager      │ ⚙️  Platform Dev      │"
echo "├──────────────────────┤                      │"
echo "│ 🔧 SRE               │                      │"
echo "└──────────────────────┴──────────────────────┘"
echo ""
echo "📌 添加业务 domain:"
echo "   Ctrl+B 然后 % (左右分屏) 或 \" (上下分屏)"
echo "   cd ~/mason-hub && claude"
echo "   进去后: 读取 agents/EMP_0003.md，你是电商 Manager"
echo ""
echo "🔑 快捷键:"
echo "   切换 pane:    Ctrl+B 然后方向键"
echo "   脱离(后台):   Ctrl+B 然后 D"
echo "   重新连接:     tmux attach -t hq"
echo ""

# 自动 attach
tmux attach -t "$SESSION"
