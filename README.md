# 后AI研究所 · Labs

**关注人的处境，开拓文明的可能。**

后AI研究所的交互项目目录与静态原型集合。项目围绕技术、经济、产业、文明与未来生活展开，包含交互模型、三维沙盘、研究工具和游戏。

网站入口：<https://postai-inst.github.io/labs/>。发布状态以 GitHub Pages 的部署记录为准。

完整初始源码保存在本仓库 Release 的 `postai-labs-source-20261124.zip` 附件中。`source-archive.json` 固定其字节数和 SHA-256；`main` 保存目录、首页、维护脚本和后续增量文件。构建先校验并展开源包，再覆盖 `main` 的更新。GitHub Actions 仅有源码读取与 Pages 发布权限，不回写仓库。

## 目录结构

```text
index.html                 自动生成的完整首页
projects.json              项目与分类的唯一目录数据源
projects/<project>/        新增项目及对初始源包的文件覆盖
assets/                    首页样式、交互脚本与品牌素材
scripts/build_index.py     从目录数据生成首页
scripts/audit.py           检查目录遗漏与本地依赖
scripts/materialize.py     校验并展开完整源文件
source-archive.json        初始源包地址与完整性校验
.github/workflows/         提交及定期目录核查
```

首页不依赖外部服务或 JavaScript 框架。即使禁用 JavaScript，完整项目列表仍可阅读；搜索、分类和状态筛选在浏览器本地执行。筛选条件写入地址栏，可直接分享某个专题的筛选结果。

## 添加或更新项目

1. 在当前仓库检出目录中，将新增项目或需要修改的文件放在 `projects/<stable-slug>/`，保持资源相对路径正确。浏览器入口通常是 `index.html`。初始项目的完整文件位于 Release 源包；修改已有文件前，可先用下方命令展开完整树，再把需要编辑的文件按相同相对路径复制回仓库。仅编辑临时预览目录不会更新 `main`。
2. 在 `projects.json` 添加或更新对应条目。保留已有 `id` 和目录名，让旧链接继续有效。
3. 核对公开内容、资源完整性、数据出处与已知限制。不要提交凭据、临时下载链接、私人聊天记录、合同或未经公开授权的研究材料。
4. 更新目录的 `updated_at`，然后运行以下命令。

```bash
labs_preview=$(mktemp -d -t postai-labs-preview.XXXXXX)
python3 scripts/materialize.py --output "$labs_preview"
python3 "$labs_preview/scripts/build_index.py"
cp "$labs_preview/index.html" ./index.html
python3 scripts/build_index.py --check
python3 "$labs_preview/scripts/audit.py" --output /tmp/postai-labs-audit.json
```

以上命令从仓库根目录执行，每次使用新的空预览目录。**必须把生成的 `index.html` 复制回仓库，并与 `projects.json`、变更后的项目文件一起提交**；只重建临时目录会导致 CI 的首页一致性检查失败。在同一终端中启动本地预览：

```bash
python3 -m http.server 8000 --directory "$labs_preview"
```

打开 `http://localhost:8000/`，检查项目首页及其关键交互。只有静态检查通过并不代表项目的 WebGL、动态网络请求或外部服务全部可用。

### 删除或迁移初始文件

初始源包固定不变。只从 `main` 删除一个覆盖文件，会让源包中的旧文件重新出现。需要从最终站点移除某个初始文件时，把它的仓库相对路径加入 `source-archive.json` 的 `exclude_paths`，并同步修改目录与引用。排除操作在文件覆盖之后执行，因此排除路径也会移除同路径的覆盖文件。不要用空路径、`.` 或整个项目根目录作为替代性的批量清理操作。

例如，退役一个已确认不再使用的旧入口时可登记 `"exclude_paths": ["projects/example/legacy.html"]`。重新展开到另一个空目录并审计，确认没有留下引用该文件的链接。

### 目录数据格式

```json
{
  "schema_version": 1,
  "base_path": "/labs/",
  "updated_at": "2026-11-24",
  "categories": [
    {"id": "futures", "label": "未来生活与游戏", "description": "体验技术与制度变化带来的日常后果"}
  ],
  "projects": [
    {
      "id": "example-project",
      "title": "项目标题",
      "description": "描述可以探索的问题，以及用户可以调整或体验的内容。",
      "category": "futures",
      "tags": ["未来生活", "交互模型"],
      "entry": "projects/example-project/index.html",
      "status": "ready",
      "kind": "交互模型",
      "updated_at": "2026-11-24",
      "featured": true,
      "notes": "如存在已知限制，在这里简明说明。",
      "source": {"label": "公开项目资料", "url": "https://example.org/project"},
      "auxiliary_entries": []
    }
  ]
}
```

`id` 使用小写字母、数字与连字符且不得重复。`category` 必须指向已有分类。`entry` 可以是仓库中的相对路径，或实际核验过的外部 HTTP(S) 地址。

| 字段 | 用途 |
| --- | --- |
| `status: ready` | 可在目录入口直接体验的项目 |
| `status: external` | 保留在其他站点的项目入口 |
| `status: limited` | 已知部分功能受限，必须配合 `notes` 说明 |
| `featured: true` | 纳入首页精选区域，按日期最多显示四个 |
| `source` | 可选公开来源；不应填写私人聊天、私有文件或临时下载地址 |
| `auxiliary_entries` | 可选附属 HTML 路径列表；这些属于同一项目，不另算独立项目 |

`updated_at` 表示该版本或目录条目的整理日期，不自动代表原研究数据的新鲜程度。模型假设、数据日期和证据范围应由各项目自己的说明保留。

## 自动核查与遗漏检查

`Labs catalogue and Pages` 工作流在向 `main` 提交、提交拉取请求、手动触发，以及每周一北京时间约 09:17（UTC 01:17）运行。GitHub 的定时队列可能延迟。

工作流只读取仓库并保存审计报告，不自动改写项目。它检查：

- `projects.json` 与生成的 `index.html` 是否一致；
- 项目 ID、分类、日期与入口是否合法，是否存在重复；
- 入口文件是否存在；
- `projects/**/index.html` 是否已纳入目录或标为同一项目的附属页；
- 其他文件名的 HTML 是否可从目录到达或明确登记为附属页；
- 静态 HTML、CSS 与字面量模块导入引用的本地文件是否存在；
- 是否残留不可发布的临时路径。

报告会列出外部 URL，但默认不对它们做网络访问。动态 `fetch()`、运行时拼接的资源地址、外部 CDN 可用性、WebGL 渲染和完整游戏流程需要另外验证。

**仓库工作流只能发现仓库内遗漏。** 查找其他对话、新生成文件和新在线项目需要由另行配置的定时助手执行，再把确认可公开、可运行的项目及其资源提交到这里。失败的来源读取应保留为待核查项，不能据此认定没有新增项目。

## GitHub Pages 发布

本仓库提供静态页面，附带 `Labs catalogue and Pages` 工作流。在 GitHub Pages 设置中将 Source 设为 **GitHub Actions**。提交至 `main` 或手动触发后，工作流先检查目录和本地资源，再上传静态站点并部署。每次发布后应核对部署结果及项目深层链接。根路径目标为 `/labs/`，请优先使用相对资源路径，避免把原站点的绝对 `/assets/` 路径直接搬入项目。

发布制品来自经过校验的初始源包与仓库增量合成后的静态目录。因此，仓库中只应保留已确认可公开的内容；不要把内部盘点记录、私人来源、敏感配置或未公开附件放入仓库，即使它们没有出现在首页。

仓库未自动附加开源许可证。各项目原有来源、许可及署名应保留；第三方材料按其自身许可使用。
