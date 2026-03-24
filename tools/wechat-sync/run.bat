@echo off
chcp 65001 >nul
echo ========================================
echo   素仁轩 - 微信聊天分析一键运行
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

:: 设置 API Key (首次使用需要填写)
if "%DEEPSEEK_API_KEY%"=="" (
    echo [提示] 首次使用请设置 DeepSeek API Key
    echo   方法1: 在系统环境变量中添加 DEEPSEEK_API_KEY
    echo   方法2: 在下面直接输入
    echo.
    set /p DEEPSEEK_API_KEY="请输入 API Key (sk-xxx): "
)

:: 默认解密目录
set DECRYPTED_DIR=%~dp0decrypted
if not exist "%DECRYPTED_DIR%" (
    echo [提示] 默认目录 decrypted\ 不存在
    set /p DECRYPTED_DIR="请输入解密后的数据库目录路径: "
)

echo.
echo [1/3] 解码微信消息...
python "%~dp0export_chat.py" "%DECRYPTED_DIR%"
if errorlevel 1 (
    echo [错误] 解码失败
    pause
    exit /b 1
)

echo.
echo [2/3] AI 分析 + 上传素仁轩...
python "%~dp0analyze_chat.py" --db "%DECRYPTED_DIR%" --incremental --upload

echo.
echo [3/3] 完成!
echo ========================================
echo   分析结果已上传到素仁轩后台
echo   Mason 可以在 /wechat-insights 查看
echo ========================================
pause
