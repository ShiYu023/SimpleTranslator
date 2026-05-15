# QuickSwitch

> vibe coding 产物 — 与 AI 对话生成

一个极简的 Windows 桌面翻译工具，基于 GLM API，窗口常驻置顶，输入即译，自动复制。

## 环境

- Python 3.11
- 依赖：`customtkinter`、`requests`、`pyperclip`

## 使用

1. 双击 `run.bat` 启动
2. 点击「设置」填入 GLM API Key（https://bigmodel.cn/apikey/platform）
3. 顶部切换 `C → E`（中译英）或 `E → C`（英译中）
4. 输入文字，按 `Ctrl+Enter` 或点击「执行」
5. 结果自动复制到剪贴板
6. 点击「清屏」或切换翻译模式自动清空

## 文件

```
translate_app.py   — 主程序
run.bat            — 启动脚本（conda 环境）
config.json        — 运行时生成，存 API Key 和偏好设置
```

## 代码结构

| 模块 | 职责 |
|------|------|
| `load_config / save_config` | JSON 配置文件读写 |
| `TranslateApp.__init__` | 窗口初始化、置顶、加载配置 |
| `_build_ui` | 构建全部 UI 组件（文本框、按钮、状态栏） |
| `_on_first_key` | 输入框占位符自动清除 |
| `_on_mode_changed` | 翻译方向切换 + 自动清屏 |
| `_execute` | 触发翻译，启动后台线程调用 API |
| `_call_api` | 调用 GLM Chat API（OpenAI 兼容格式） |
| `_on_success / _on_error` | 在主线程更新 UI |
| `_clear / _copy_result` | 清屏、手动复制 |
| `_open_settings` | 设置对话框（API Key、模型选择） |

## API

接口：`https://open.bigmodel.cn/api/paas/v4/chat/completions`

使用 system prompt 约束模型只输出译文，temperature=0.3 保证稳定性。
