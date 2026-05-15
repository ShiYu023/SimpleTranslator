import customtkinter as ctk
import requests
import pyperclip
import json
import os
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

SYSTEM_PROMPTS = {
    "cn2en": (
        "你是一个专业的中译英翻译助手。"
        "请将用户输入的中文翻译成自然流畅的英文。"
        "只输出英文翻译结果，不要输出任何解释、说明或额外的文字。"
        "保持原文的语气和风格。"
    ),
    "en2cn": (
        "You are a professional English-to-Chinese translator. "
        "Translate the user's English input into natural, fluent Chinese. "
        "Only output the Chinese translation result, no explanations or extra text. "
        "Preserve the tone and style of the original."
    ),
}

PLACEHOLDERS = {
    "cn2en": "输入中文...",
    "en2cn": "Enter English...",
}

STATUS_TRANSLATING = {
    "cn2en": "正在翻译...",
    "en2cn": "Translating...",
}
STATUS_DONE = {
    "cn2en": "已完成，已自动复制到剪贴板",
    "en2cn": "Done, copied to clipboard",
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"api_key": "", "model": "glm-4-flash", "mode": "cn2en"}


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


class TranslateApp:
    def __init__(self):
        self.config = load_config()
        self._mode = self.config.get("mode", "cn2en")

        self.window = ctk.CTk()
        self.window.title("QuickSwitch")
        self.window.geometry("520x320")
        self.window.resizable(True, True)
        self.window.minsize(400, 260)
        self.window.attributes("-topmost", True)

        self._build_ui()
        self._check_api_key()

    def _build_ui(self):
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(0, weight=0)
        self.window.grid_rowconfigure(1, weight=1)
        self.window.grid_rowconfigure(2, weight=1)
        self.window.grid_rowconfigure(3, weight=0)
        self.window.grid_rowconfigure(4, weight=0)

        # 顶部栏：模式切换 + 设置按钮
        top_bar = ctk.CTkFrame(self.window, fg_color="transparent")
        top_bar.grid(row=0, column=0, padx=16, pady=(12, 0), sticky="ew")
        top_bar.grid_columnconfigure(1, weight=1)

        self.mode_seg = ctk.CTkSegmentedButton(
            top_bar, values=["C → E", "E → C"],
            font=ctk.CTkFont(size=12),
            command=self._on_mode_changed
        )
        self.mode_seg.grid(row=0, column=0, sticky="w")
        self.mode_seg.set("C → E" if self._mode == "cn2en" else "E → C")

        self.settings_btn = ctk.CTkButton(
            top_bar, text="设置", width=50, height=26,
            font=ctk.CTkFont(size=11),
            command=self._open_settings
        )
        self.settings_btn.grid(row=0, column=2)

        # 输入框
        self.input_text = ctk.CTkTextbox(
            self.window, font=ctk.CTkFont(size=13),
            wrap="word", height=80
        )
        self.input_text.grid(row=1, column=0, padx=16, pady=(10, 4), sticky="nsew")
        self.input_text.bind("<Control-Return>", lambda e: self._execute())

        self._input_has_placeholder = False
        self._show_placeholder()
        self.input_text.bind("<Key>", self._on_first_key)
        self.input_text.bind("<FocusIn>", self._on_first_key)
        self.input_text.bind("<FocusOut>", self._on_input_focus_out)

        # 输出框
        self.output_text = ctk.CTkTextbox(
            self.window, font=ctk.CTkFont(size=13),
            wrap="word", height=80, state="disabled"
        )
        self.output_text.grid(row=2, column=0, padx=16, pady=(4, 4), sticky="nsew")

        # 按钮行
        btn_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        btn_frame.grid(row=3, column=0, padx=16, pady=(4, 4), sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)

        self.exec_btn = ctk.CTkButton(
            btn_frame, text="执行 (Ctrl+Enter)", height=34,
            font=ctk.CTkFont(size=13),
            command=self._execute
        )
        self.exec_btn.grid(row=0, column=0, sticky="ew")

        self.copy_btn = ctk.CTkButton(
            btn_frame, text="复制", width=50, height=34,
            font=ctk.CTkFont(size=12),
            fg_color="#444444", hover_color="#555555",
            command=self._copy_result
        )
        self.copy_btn.grid(row=0, column=1, padx=(8, 0))

        self.clear_btn = ctk.CTkButton(
            btn_frame, text="清屏", width=50, height=34,
            font=ctk.CTkFont(size=12),
            fg_color="#444444", hover_color="#555555",
            command=self._clear
        )
        self.clear_btn.grid(row=0, column=2, padx=(8, 0))

        # 状态栏
        self.status_label = ctk.CTkLabel(
            self.window, text="就绪",
            font=ctk.CTkFont(size=11),
            text_color="gray55"
        )
        self.status_label.grid(row=4, column=0, padx=16, pady=(2, 10), sticky="w")

    def _show_placeholder(self):
        self.input_text.delete("1.0", "end")
        self.input_text.insert("1.0", PLACEHOLDERS[self._mode])
        self.input_text.configure(text_color="gray55")
        self._input_has_placeholder = True

    def _on_mode_changed(self, value):
        self._mode = "cn2en" if value == "C → E" else "en2cn"
        self.config["mode"] = self._mode
        save_config(self.config)
        self._clear()

    def _on_first_key(self, event):
        if self._input_has_placeholder:
            self.input_text.delete("1.0", "end")
            self.input_text.configure(text_color=("black", "white"))
            self._input_has_placeholder = False

    def _on_input_focus_out(self, event):
        content = self.input_text.get("1.0", "end-1c").strip()
        if not content:
            self._show_placeholder()

    def _check_api_key(self):
        if not self.config.get("api_key"):
            self.status_label.configure(text="请先点击「设置」填入 GLM API Key", text_color="#ff9944")
            self.exec_btn.configure(state="disabled")
        else:
            self.exec_btn.configure(state="normal")

    def _open_settings(self):
        dialog = ctk.CTkToplevel(self.window)
        dialog.title("设置")
        dialog.geometry("440x280")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        dialog.grab_set()

        dialog.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            dialog, text="GLM API 设置",
            font=ctk.CTkFont(size=15, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=(16, 12), sticky="w")

        ctk.CTkLabel(dialog, text="API Key", font=ctk.CTkFont(size=12)).grid(
            row=1, column=0, padx=20, pady=(0, 2), sticky="w"
        )
        api_key_entry = ctk.CTkEntry(dialog, font=ctk.CTkFont(size=12), show="*")
        api_key_entry.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        if self.config.get("api_key"):
            api_key_entry.insert(0, self.config["api_key"])

        ctk.CTkLabel(dialog, text="模型", font=ctk.CTkFont(size=12)).grid(
            row=3, column=0, padx=20, pady=(0, 2), sticky="w"
        )
        model_menu = ctk.CTkOptionMenu(
            dialog, font=ctk.CTkFont(size=12),
            values=["glm-4-flash", "glm-4", "glm-4-plus"],
            width=200
        )
        model_menu.grid(row=4, column=0, padx=20, pady=(0, 16), sticky="w")
        model_menu.set(self.config.get("model", "glm-4-flash"))

        ctk.CTkLabel(
            dialog,
            text="申请地址: https://open.bigmodel.cn\n   glm-4-flash 免费额度充足，翻译够用",
            font=ctk.CTkFont(size=11),
            text_color="gray55",
            justify="left"
        ).grid(row=5, column=0, padx=20, pady=(0, 10), sticky="w")

        def save():
            self.config["api_key"] = api_key_entry.get().strip()
            self.config["model"] = model_menu.get()
            save_config(self.config)
            self._check_api_key()
            dialog.destroy()
            if self.config["api_key"]:
                self.status_label.configure(text="设置已保存", text_color="#44cc66")
                self.window.after(2000, lambda: self.status_label.configure(
                    text="就绪", text_color="gray55"
                ))

        ctk.CTkButton(
            dialog, text="保存", height=32,
            font=ctk.CTkFont(size=13),
            command=save
        ).grid(row=6, column=0, padx=20, pady=(0, 16))

    def _execute(self):
        if not self.config.get("api_key"):
            self.status_label.configure(text="请先设置 API Key", text_color="#ff4444")
            return

        if self._input_has_placeholder:
            return

        text = self.input_text.get("1.0", "end-1c").strip()
        if not text:
            self.status_label.configure(text="请先输入文字", text_color="#ff9944")
            return

        self.exec_btn.configure(state="disabled", text="执行中...")
        self.status_label.configure(text=STATUS_TRANSLATING[self._mode], text_color="#4499cc")

        thread = threading.Thread(target=self._call_api, args=(text,), daemon=True)
        thread.start()

    def _call_api(self, text):
        try:
            headers = {
                "Authorization": f"Bearer {self.config['api_key']}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.config.get("model", "glm-4-flash"),
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPTS[self._mode]},
                    {"role": "user", "content": text}
                ],
                "temperature": 0.3,
                "max_tokens": 2048
            }

            resp = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            data = resp.json()

            if resp.status_code == 200 and "choices" in data:
                result = data["choices"][0]["message"]["content"].strip()
                self.window.after(0, lambda: self._on_success(result))
            else:
                error_msg = data.get("error", {}).get("message", f"HTTP {resp.status_code}")
                self.window.after(0, lambda: self._on_error(error_msg))

        except requests.exceptions.Timeout:
            self.window.after(0, lambda: self._on_error("请求超时，请检查网络"))
        except Exception as e:
            self.window.after(0, lambda: self._on_error(str(e)))

    def _on_success(self, result):
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", result)
        self.output_text.configure(state="disabled")

        try:
            pyperclip.copy(result)
        except Exception:
            pass

        self.exec_btn.configure(state="normal", text="执行 (Ctrl+Enter)")
        self.status_label.configure(text=STATUS_DONE[self._mode], text_color="#44cc66")
        self.window.after(3000, lambda: self.status_label.configure(
            text="就绪", text_color="gray55"
        ))

    def _on_error(self, error_msg):
        self.exec_btn.configure(state="normal", text="执行 (Ctrl+Enter)")
        self.status_label.configure(text=f"失败: {error_msg}", text_color="#ff4444")

    def _clear(self):
        self._show_placeholder()
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.configure(state="disabled")
        self.status_label.configure(text="就绪", text_color="gray55")

    def _copy_result(self):
        content = self.output_text.get("1.0", "end-1c").strip()
        if content:
            try:
                pyperclip.copy(content)
                self.status_label.configure(text="已复制到剪贴板", text_color="#44cc66")
                self.window.after(2000, lambda: self.status_label.configure(
                    text="就绪", text_color="gray55"
                ))
            except Exception:
                self.status_label.configure(text="复制失败", text_color="#ff4444")

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    app = TranslateApp()
    app.run()
