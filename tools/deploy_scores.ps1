# PTE 出分墙 · 真实截图一键部署
#
# 用法：
#   1) 把真实出分截图丢进  D:\PTE-Exam-System\publish\assets\scores\
#      支持 .jpg/.jpeg/.png/.webp/.bmp，文件名任意（建议 1.jpg 2.jpg ...）
#   2) （可选）编辑同目录 captions.json 配文案：
#      [ { "file": "1.jpg", "who": "Luna", "text": "口语 58->73，两周上岸" } ]
#      没有也能跑，自动用「出分截图 1/2/3」当文案
#   3) 运行：
#        $env:GH_TOKEN = "ghp_你的PAT"
#        powershell -ExecutionPolicy Bypass -File tools\deploy_scores.ps1
#   4) 约 1 分钟后刷新落地页即可看到真实截图轮播
#
# 其他：-MaxWidth 900  -Quality 82  -SourceDir <目录>  -RestoreText(恢复文字版)
# 安全：token 只从环境变量 GH_TOKEN 读取，脚本内不含任何密钥。
param(
  [string]$SourceDir = "D:\PTE-Exam-System\publish\assets\scores",
  [string]$IndexHtml = "D:\PTE-Exam-System\publish\index.html",
  [string]$Repo = "sunav66/pte-exam-system",
  [string]$Branch = "main",
  [int]$MaxWidth = 900,
  [int]$Quality = 82,
  [switch]$RestoreText
)
$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
if (-not $env:GH_TOKEN) { Write-Host "[X] 请先设置 GH_TOKEN 环境变量"; exit 1 }

$H = @{ Authorization = "token $env:GH_TOKEN"; "User-Agent" = "pte-score-deploy"; Accept = "application/vnd.github+json" }
$Api = "https://api.github.com/repos/$Repo/contents"
$Utf8 = New-Object System.Text.UTF8Encoding($false)

function Get-Sha([string]$path) {
  try { return (Invoke-RestMethod -Headers $H -Uri "$Api/$path`?ref=$Branch" -Method Get).sha } catch { return $null }
}

function Put-File([string]$path, [byte[]]$bytes, [string]$msg) {
  $body = @{ branch = $Branch; message = $msg; content = [Convert]::ToBase64String($bytes) }
  $sha = Get-Sha $path
  if ($sha) { $body.sha = $sha }
  Invoke-RestMethod -Headers $H -Uri $Api/$path -Method Put -Body ($body | ConvertTo-Json) -ContentType "application/json" | Out-Null
  Write-Host ("  [OK] {0}  ({1} KB)" -f $path, [Math]::Round($bytes.Length / 1KB, 1))
}

Add-Type -AssemblyName System.Drawing

# 压缩为 JPEG（最长边 MaxWidth），返回字节数组
function Convert-Image([string]$src, [string]$workDir) {
  $img = [System.Drawing.Image]::FromFile($src)
  try {
    $w = $img.Width; $h = $img.Height
    $scale = [Math]::Min(1.0, [Math]::Min($MaxWidth / [Math]::Max($w, 1), $MaxWidth / [Math]::Max($h, 1)))
    $nw = [Math]::Max(1, [int]($w * $scale)); $nh = [Math]::Max(1, [int]($h * $scale))
    $bmp = New-Object System.Drawing.Bitmap($nw, $nh)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.DrawImage($img, 0, 0, $nw, $nh); $g.Dispose()
    $out = Join-Path $workDir ("{0}.jpg" -f [Guid]::NewGuid().ToString("N"))
    $codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq "image/jpeg" } | Select-Object -First 1
    $ep = New-Object System.Drawing.Imaging.EncoderParameters(1)
    $ep.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, [long]$Quality)
    $bmp.Save($out, $codec, $ep); $bmp.Dispose()
    return [System.IO.File]::ReadAllBytes($out)
  } finally { $img.Dispose() }
}

# ---------- 读取 / 写回 index.html 的出分墙区块 ----------
function Get-Html { [System.IO.File]::ReadAllText($IndexHtml, [System.Text.Encoding]::UTF8) }
function Set-Html([string]$text) {
  [System.IO.File]::WriteAllText($IndexHtml, $text, $Utf8)
  $bytes = [System.IO.File]::ReadAllBytes($IndexHtml)
  Put-File "index.html" $bytes "Deploy score wall update"
}

# 出分墙区块正则（slides 开头到 dots 前）
$Rx = '(?s)(<div class="slides" id="slides"[^>]*>).*?(</div>\s*<div class="dots")'

if ($RestoreText) {
  Write-Host "==> 恢复文字版出分墙"
  $html = Get-Html
  $restore = '<div class="slides" id="slides">
        <div class="slide active"><span class="who">Luna · 澳洲留学</span>：PTE 65 分手！口语 58→73，靠离线狂刷 + AI 批改 🎉</div>
        <div class="slide"><span class="who">阿哲 · 移民加分</span>：写作 <span class="sc">79</span>！¥6.6 平替真香，机构贵到离谱。</div>
        <div class="slide"><span class="who">Mia · 二战党</span>：听力 <span class="sc">79</span>，机经题库全覆盖，刷题不心疼。</div>
      </div>
      <div class="dots"'
  $html = [System.Text.RegularExpressions.Regex]::Replace($html, $Rx, $restore)
  $html = $html.Replace("真实出分截图（已获买家授权，满分感谢）。", "示例内容，请替换为真实出分截图 / 买家授权喜报以增强转化。")
  Set-Html $html
  Write-Host "==> 已恢复文字版，落地页约 1 分钟后更新"
  exit 0
}

# ---------- 模式 B：部署真实截图 ----------
if (-not (Test-Path $SourceDir)) { Write-Host "[X] 截图目录不存在: $SourceDir"; exit 1 }
$files = Get-ChildItem $SourceDir -File | Where-Object { $_.Extension -match '^\.(jpg|jpeg|png|webp|bmp)$' } | Sort-Object Name
if (-not $files) { Write-Host "[X] 目录里没有图片"; exit 1 }
Write-Host ("==> 发现 {0} 张截图" -f $files.Count)

# captions.json（可选）
$caps = @{}
$capFile = Join-Path $SourceDir "captions.json"
if (Test-Path $capFile) {
  try { foreach ($c in (Get-Content $capFile -Raw -Encoding UTF8 | ConvertFrom-Json)) { $caps[$c.file.ToLower()] = $c } } catch { Write-Host "  [!] captions.json 解析失败，忽略" }
}

$work = Join-Path $env:TEMP ("pte_scores_" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $work | Out-Null
$slides = New-Object System.Collections.Generic.List[string]
$i = 0
foreach ($f in $files) {
  $i++
  $imgBytes = Convert-Image $f.FullName $work
  $name = "{0}.jpg" -f ($f.BaseName -replace '[^A-Za-z0-9_-]', '_')
  Put-File "assets/scores/$name" $imgBytes "Add score screenshot $name"
  $cap = $caps[$f.Name.ToLower()]
  if ($cap) { $capHtml = '<span class="who">' + $cap.who + '</span>：' + $cap.text } else { $capHtml = "出分截图 $i（已获授权）" }
  $cls = "slide"; if ($i -eq 1) { $cls = "slide active" }
  $slides.Add(('        <div class="{0}"><img src="assets/scores/{1}" alt="PTE 出分截图 {2}" style="max-width:100%;border-radius:8px"><div style="margin-top:6px;font-size:13px">{3}</div></div>' -f $cls, $name, $i, $capHtml))
  Start-Sleep -Milliseconds 500
}
Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue

$slidesHtml = '<div class="slides" id="slides" style="min-height:420px">
' + ($slides -join "`n") + '
      </div>
      <div class="dots"'
$html = Get-Html
$html = [System.Text.RegularExpressions.Regex]::Replace($html, $Rx, $slidesHtml.Replace('$', '$$'))
$html = $html.Replace("示例内容，请替换为真实出分截图 / 买家授权喜报以增强转化。", "真实出分截图（已获买家授权，满分感谢）。有出分欢迎晒分返现 ¥3~6。")
Set-Html $html
Write-Host "==> 完成！落地页约 1 分钟后显示真实出分墙："
Write-Host "    https://sunav66.github.io/pte-exam-system/"