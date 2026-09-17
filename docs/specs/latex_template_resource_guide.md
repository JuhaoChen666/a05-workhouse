# LaTeX 模板资源管理与规范指南 (Phase 0)

本文档规范基于 LaTeX 的简历模板在系统代码库中的组织形式、目录结构、元数据协议及运行时解析流程。

---

## 1. 资源存放目录

按照项目工程规范，所有内置 LaTeX 模板作为后端静态资源统一部署在：
```
Springboot-backend/src/main/resources/templates/latex/
```

### 目录层级结构
```
Springboot-backend/src/main/resources/templates/latex/
├── billryan-classic/                       # 模板 1: 中文经典单栏模板 (IT研发)
│   ├── template.json                       # 模板元数据清单与占位符协议
│   ├── resume.cls                          # LaTeX 文档类定制文件
│   └── resume.tex.j2                       # Jinja2 参数化 LaTeX 模板源码
│
├── modern-twocol/                          # 模板 2: 现代两栏高信息密度模板
│   ├── template.json                       # 模板元数据清单与占位符协议
│   └── resume.tex.j2                       # Jinja2 参数化两栏 LaTeX 源码
│
├── jakes-resume/                           # 模板 3: Jake's Resume 极简 ATS 单栏
│   ├── template.json                       # 模板元数据清单与占位符协议
│   └── resume.tex.j2                       # Jinja2 参数化单栏 ATS 源码
│
├── huajh-resume/                           # 模板 4: 大厂技术求职精简单页
│   ├── template.json                       # 模板元数据清单与占位符协议
│   └── resume.tex.j2                       # Jinja2 参数化国内大厂单页源码
│
├── altacv/                                 # 模板 5: AltaCV 现代非对称双栏 (技能胶囊)
│   ├── template.json                       # 模板元数据清单与占位符协议
│   ├── altacv.cls                          # AltaCV 文档类定义
│   └── resume.tex.j2                       # Jinja2 参数化非对称两栏源码
│
└── zheyuye-chinese/                        # 模板 6: zheyuye 极简中文单栏 (零依赖)
    ├── template.json                       # 模板元数据清单与占位符协议
    └── resume.tex.j2                       # Jinja2 参数化轻量源码
```

---

## 2. 模板元数据规范 (`template.json`)

每个模板目录下必须包含一个标准 `template.json` 文件，用于指导后端的模板校验、前端渲染配置与生成选项匹配：

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `id` | `string` | 模板全局唯一标识（如 `tpl-billryan-classic`） |
| `name` | `string` | 模板用户界面展示名称 |
| `version` | `string` | 语义化版本号，便于简历库记录生成时的版本快照 |
| `description` | `string` | 模板特性与排版建议说明 |
| `engine` | `string` | 编译引擎，默认 `xelatex` |
| `cjk_package` | `string` | 中文处理宏包，推荐 `xeCJK` |
| `recommended_pages` | `number[]` | 推荐页数（如 `[1]` 表示专为单页优化） |
| `supports_avatar` | `boolean` | 是否支持证件照插槽 |
| `default_avatar_style` | `string` | `tikz_overlay_top_right` (右上角悬浮) 或 `sidebar_top` (侧边栏顶部) |
| `entry_file` | `string` | 主模板文件名（通常为 `resume.tex.j2`） |
| `supported_sections` | `string[]` | 支持渲染的经历分类与信息块 |
| `placeholders` | `object` | 模板所需字段结构契约字典 |

---

## 3. 模板占位符与 Jinja2 语法规范

为确保代码健壮性与防止 LaTeX 命令注入（LaTeX Injection），所有变量渲染遵循以下原则：

1. **严格使用 `latex_escape` 过滤器**：
   ```jinja2
   {{ basic_info.name | latex_escape }}
   ```
2. **列表迭代结构化**：
   ```jinja2
   {% for proj in projects %}
   \datedsubsection{ {{ proj.title | latex_escape }} }{ {{ proj.date_range | latex_escape }} }
   \begin{itemize}
     {% for b in proj.bullets %}
     \item {{ b | latex_escape }}
     {% endfor %}
   \end{itemize}
   {% endfor %}
   ```
3. **照片开关条件注入**：
   ```jinja2
   {% if options.show_avatar and basic_info.avatar_path %}
   \begin{tikzpicture}[remember picture, overlay]
     \node[anchor=north east, xshift=-1.8cm, yshift=-1.2cm] at (current page.north east) {
       \includegraphics[height=2.8cm]{ {{ basic_info.avatar_path }} }
     };
   \end{tikzpicture}
   {% endif %}
   ```

---

## 4. 后端加载与编译生命周期

1. **资源读取**：
   - Spring Boot 或 FastAPI 引擎通过类路径（Classpath）或挂载共享卷读取 `templates/latex/{template_id}/` 模板资源；
2. **数据组装与渲染**：
   - 提取个人经历库中选中的原子经历，经过 AI JD 润色后映射为 JSON 上下文；
   - Jinja2 引擎将数据安全注入 `resume.tex.j2`，生成临时工作目录下的 `job_{id}/main.tex`；
3. **隔离编译**：
   - 启动沙箱进程运行 `xelatex -interaction=nonstopmode -halt-on-error -no-shell-escape main.tex`；
   - 检查退出码与超时状态，若成功则收集 `main.pdf` 并上传至持久化对象存储/文件系统，输出下载 URL 与源码。
