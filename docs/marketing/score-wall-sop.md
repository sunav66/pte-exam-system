# 出分墙 SOP：买家晒单 → 上线（1 页照做）

> 目标：收到买家出分截图后，**3 分钟内**让它在落地页轮播展示。
> 落地页：https://sunav66.github.io/pte-exam-system/

---

## 0. 一次性准备（只做一次）

1. 生成新 GitHub PAT（旧的用完就撤销）：
   GitHub → 右上角头像 → **Settings → Developer settings → Personal access tokens → Tokens (classic)** → Generate new token → 勾 `repo` → 复制 `ghp_...`
2. 本机设置（当前窗口有效）：
   ```powershell
   $env:GH_TOKEN = "ghp_你的新PAT"
   ```
   （想永久生效：把它加进 Windows「用户环境变量」GH_TOKEN）

---

## 1. 收图（微信）

- 买家出分后主动索图的话术：
  「恭喜出分！发我成绩单截图，**返现 ¥3~6 或送激活码 1 个**，截图会展示在官网出分墙（可打码）。」
- **必做**：拿到截图先征得展示同意；用微信图片编辑或画图把**姓名/邮箱/准考证号打码**，其余保留。

## 2. 存图

把打好码的截图存到：

```
D:\PTE-Exam-System\publish\assets\scores\
```

- 支持 `jpg / jpeg / png / webp / bmp`，命名随意（建议 `1.jpg 2.jpg …`）
- 脚本会自动压缩到 900px / JPEG，不用自己处理

## 3. 配文案（可选但强烈建议）

编辑同目录 `captions.json`（对应文件名写一行）：

```json
[
  { "file": "1.jpg", "who": "Luna", "text": "口语 58→73，两周上岸！" },
  { "file": "2.jpg", "who": "阿哲", "text": "写作 79，移民加分到手" }
]
```

不配也行，会显示「出分截图 1（已获授权）」。

## 4. 一条命令上线

```powershell
powershell -ExecutionPolicy Bypass -File D:\PTE-Exam-System\tools\deploy_scores.ps1
```

脚本自动完成：压缩 → 传 GitHub → 重写出分墙 → 部署。
**约 1 分钟后**刷新 https://sunav66.github.io/pte-exam-system/ （看不到就 Ctrl+F5 强刷）。

## 5. 回滚 / 更换

| 想做什么 | 命令 |
|---|---|
| 恢复文字版喜报（隐藏所有截图） | 同上加参数 `-RestoreText` |
| 换一批截图 | 把目录里的图换成新的，重跑步骤 4（旧图会被轮播替换，仓库里旧文件无害可不管） |
| 只改文案 | 改 `captions.json` 后重跑步骤 4 |

---

## 常见问题

| 现象 | 处理 |
|---|---|
| `[X] 请先设置 GH_TOKEN` | 关掉窗口后重开，重新执行第 0 步第 2 条 |
| `[X] 截图目录不存在 / 没有图片` | 确认图放在 `publish\assets\scores\` 且扩展名是图片 |
| captions.json 报「解析失败」 | JSON 格式错（少逗号/引号），照上面模板改；或直接删掉该文件用默认文案 |
| 上传时报 422 / 409 | 网络抖动，**直接重跑一次**即可 |
| 部署成功但页面没变 | Pages 构建 1~2 分钟；再等会儿 + Ctrl+F5；还不行检查是否看的是缓存 |
| PAT 失效（401） | 第 0 步重新生成 PAT（旧的同时撤销） |

## 红线（务必遵守）

- 未经买家同意不上架截图；展示前打码个人信息。
- 不 P 图改分数——假喜报被识破口碑即崩。
- PAT 等同仓库钥匙，不外发、不写进任何文件（本脚本只读环境变量）。
