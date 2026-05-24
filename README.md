# Personal AI — 个人数据层

> 一个本地运行的 AI 聚合工具。在同一个界面里使用 DeepSeek、GPT、Claude、Groq，
> 所有对话自动保存，切换供应商时历史可查、上下文可注入。

---

## 适合谁用

- 想用一个界面用多个 AI，不用开好几个网页
- 希望在 DeepSeek 聊过的内容，切换到 GPT 时还能看到
- 不想让聊天记录留在 AI 公司的服务器上
- 能用鼠标键盘，但不想碰命令行和代码

---

## 快速开始（3 步）

### 第 1 步：装 Python

如果你电脑上已经装了 Python，跳过这一步。

1. 打开 https://www.python.org/downloads/
2. 下载最新版 Python（Windows 选 64-bit installer）
3. 双击安装，**务必勾选"Add Python to PATH"**（在安装界面最下面）
4. 一路点"Next"装完

验证安装是否成功：按 `Win + R`，输入 `cmd` 回车，在黑窗口里输入：

```
python --version
```

如果显示 `Python 3.x.x`，说明装好了。

### 第 2 步：下载本项目

1. 打开 https://github.com/Player-2048/ai-proxy
2. 点击绿色的 **"Code"** 按钮
3. 点击 **"Download ZIP"**
4. 解压到桌面（或你习惯放软件的地方）

### 第 3 步：启动

1. 打开项目文件夹，在地址栏输入 `cmd` 回车（打开黑窗口）
2. 在黑窗口里输入：

```
pip install -r requirements.txt
```

等待跑完（可能需要 1-5 分钟，视网络而定）。

3. 然后输入：

```
py run.py
```

你会看到类似这样的内容：

```
AI Proxy starting on 127.0.0.1:8080
Opening http://127.0.0.1:8080 in browser...
```

浏览器会自动打开一个页面。如果没有自动打开，手动打开 Chrome 或 Edge，在地址栏输入：

```
http://localhost:8080
```

**大功告成。** 你现在看到的是 Personal AI 的主页。

---

## 使用指南

### 配 API Key（必须）

每个 AI 供应商都需要 API Key 才能使用。没有 API Key 的话，无法发消息。

1. 点击主页右上角的 **⚙️**（齿轮图标）
2. 你会看到四个供应商的输入框
3. 每一个输入框填对应的 API Key：

| 供应商 | 需不需要 | 去哪申请 |
|--------|---------|---------|
| DeepSeek | ✅ 推荐 | https://platform.deepseek.com/api_keys |
| OpenAI | ✅ 推荐 | https://platform.openai.com/api-keys |
| Claude | ✅ 推荐 | https://console.anthropic.com/ |
| Groq | 可选 | https://console.groq.com/keys |

4. 填完 Key 后，点旁边的 **"测试连接"** 按钮
5. 显示 ✅ 连接成功 → 说明 Key 能用
6. 显示 ❌ 失败 → 检查 Key 是否复制完整

> **Key 安全吗？** Key 存在你电脑浏览器的本地缓存里，不经过任何服务器。

### 开始聊天

1. 配好 Key 后，点左上角 **← 返回聊天**
2. 顶栏下拉框选择供应商（DeepSeek / GPT / Claude / Groq）
3. 在底部输入框输入内容，按回车发送
4. AI 回复会在对话气泡里显示

### 查历史记录

1. 点顶栏的 **📋** 按钮（右侧）
2. 右侧会弹出历史面板
3. 在搜索框里输入关键词，可以搜到过去的所有对话
4. 语义搜索会自动匹配意思相近的内容（即使关键词不完全一致）

### 把历史对话注入当前会话

1. 在历史面板里找到你想引用的对话
2. 点 **"注入当前会话"**
3. 这条对话的内容会被追加到当前对话中
4. 发送消息时，AI 会看到这些历史内容

### 切换 AI 供应商后注入历史

假设你一直在用 DeepSeek 聊项目需求，现在想切换到 GPT 继续：

1. 在顶栏下拉框切换到 GPT
2. 点 📋 打开历史面板
3. 搜索"需求"或"项目"
4. 看到之前在 DeepSeek 聊的内容，点"注入当前会话"
5. 现在 GPT 也知道你们之前聊了什么

### 导出数据

1. 点 📋 打开历史面板
2. 底部有 **"📥 导出所有数据"** 按钮
3. 点击后会下载一个 zip 包，里面包含：
   - 所有对话记录
   - 向量索引
   - 配置文件

导出后可以把 zip 包存到其他地方，或者在新电脑上导入。

---

## 常见问题

### 打开后只看到"没有可用的供应商"

没配 API Key。去 ⚙️ 页面填至少一个 Key 并测试通过。

### 发消息后一直在转圈

- 检查网络连接
- 检查 API Key 是否正确
- 切换到其他供应商试试

### 想跟朋友分享这个工具

1. 配好你的 API Key
2. **不要直接分享**——你的 Key 会暴露
3. 让对方也按本教程的第 1-3 步操作，自己申请 Key

如果需要打包成 EXE（双击即用，不需要装 Python）：

```
pip install pyinstaller
python build.py
pyinstaller personal-ai.spec
```

生成的文件在 `dist/PersonalAI.exe`，约 150-250MB。

### 浏览器打不开

手动在浏览器地址栏输入 `http://localhost:8080`。

### 可以在这里问个人 AI 吗？

不可以。这只是个工具，它不包含任何内置 AI。你需要通过 API Key 接入 DeepSeek、GPT 或 Claude。

---

## 文件结构（不用管也行）

```
ai-proxy-main/
├── run.py              ← 启动入口（双击这个不行，需命令行）
├── config.yaml         ← 供应商配置（初学者不用碰）
├── build.py            ← 打包成 EXE 的脚本
├── proxy/
│   ├── server.py       ← 后端服务
│   ├── static/         ← 前端页面（HTML / CSS / JS）
│   │   ├── index.html  ← 主页（聊天界面）
│   │   ├── style.css   ← 样式
│   │   ├── app.js      ← 交互逻辑
│   │   └── settings.html ← 设置页
│   ├── memory.py       ← 对话记忆（语义搜索）
│   └── logger.py       ← 对话记录数据库
├── data/               ← 你的数据自动存在这里
│   ├── logs.db         ← 对话记录
│   └── chroma/         ← 搜索索引
└── tests/              ← 测试（不用管）
```

---

## 升级到新版本

如果以后更新了这个工具：

1. 下载新版本 ZIP
2. 复制旧版本的 `data/` 文件夹到新版本目录
3. 运行 `py run.py`

所有历史记录都在 `data/` 里，不会丢。

---

## 用这个工具做出来的项目

这个工具本身是你用 engineering-pipeline 工作流设计出来的产物。
如果你想了解 pipeline 本身，可以读：

- `PIPELINE-QUICKSTART.md`（快速启动管道）
- `CONTEXT.md`（术语表）
- `.scratch/issues/`（5 个实现 issue）
