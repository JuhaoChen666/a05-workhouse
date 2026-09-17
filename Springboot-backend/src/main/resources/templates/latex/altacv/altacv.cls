\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{altacv}[2024/01/01 AltaCV v1.5, Modern Curriculum Vitae Class]

\DeclareOption*{\PassOptionsToClass{\CurrentOption}{article}}
\ProcessOptions\relax
\LoadClass{article}

\RequirePackage{geometry}
\geometry{left=1.2cm,right=1.2cm,top=1.2cm,bottom=1.2cm,footskip=0.5cm}

\RequirePackage{xcolor}
\RequirePackage{tikz}
\RequirePackage{paracol}
\RequirePackage{enumitem}
\RequirePackage{hyperref}
\RequirePackage{titlesec}
\RequirePackage{etoolbox}

% 默认调色板 (现代 Slate / Navy)
\definecolor{SlateGrey}{HTML}{2E2E2E}
\definecolor{LightGrey}{HTML}{666666}
\definecolor{DarkPastelBlue}{HTML}{1A5276}
\definecolor{AccentColor}{HTML}{006699}
\definecolor{TagBackground}{HTML}{EEF2F6}
\definecolor{TagBorder}{HTML}{CBD5E1}

\colorlet{heading}{DarkPastelBlue}
\colorlet{accent}{AccentColor}
\colorlet{emphasis}{SlateGrey}
\colorlet{body}{LightGrey}

\hypersetup{hidelinks, colorlinks=false}

% 个人信息存储宏
\newcommand{\name}[1]{\def\@name{#1}}
\newcommand{\tagline}[1]{\def\@tagline{#1}}
\newcommand{\personalinfo}[1]{\def\@personalinfo{#1}}
\newcommand{\photo}[2]{\def\@photoheight{#1}\def\@photopath{#2}}
\def\@photoheight{}
\def\@photopath{}

% 头部渲染命令
\newcommand{\makecvheader}{%
  \begingroup
  \ifstrempty{\@photopath}{%
    \begin{minipage}{\textwidth}
      {\Huge\bfseries\color{heading}\@name}\par\vspace{0.3ex}
      \ifdef{\@tagline}{{\large\color{accent}\@tagline}\par\vspace{0.5ex}}{}
      \ifdef{\@personalinfo}{{\small\color{body}\@personalinfo}\par}{}
    \end{minipage}
  }{%
    \begin{minipage}{\dimexpr\textwidth-\@photoheight-1cm\relax}
      {\Huge\bfseries\color{heading}\@name}\par\vspace{0.3ex}
      \ifdef{\@tagline}{{\large\color{accent}\@tagline}\par\vspace{0.5ex}}{}
      \ifdef{\@personalinfo}{{\small\color{body}\@personalinfo}\par}{}
    \end{minipage}\hfill
    \begin{minipage}{\@photoheight}
      \begin{tikzpicture}
        \clip (0,0) circle (\@photoheight/2);
        \node at (0,0) {\includegraphics[width=\@photoheight,height=\@photoheight,keepaspectratio]{\@photopath}};
      \end{tikzpicture}
    \end{minipage}
  }
  \endgroup
  \vspace{1.5ex}
}

% 节标题 CV Section
\newcommand{\cvsection}[1]{%
  \vspace{1.2ex}%
  {\color{heading}\large\bfseries\MakeUppercase{#1}}\par%
  \vspace{0.2ex}%
  {\color{accent}\rule{\linewidth}{1.5pt}}\par%
  \vspace{0.6ex}%
}

% 事件节点命令 (职位/项目/奖项)
\newcommand{\cvevent}[4]{%
  {\bfseries\color{emphasis}#1}%
  \ifstrempty{#2}{}{ \textbar\ {\color{accent}#2}}%
  \hfill%
  \ifstrempty{#3}{}{{\small\color{body}#3}}\par%
  \ifstrempty{#4}{}{%
    {\footnotesize\color{body}#4}\par%
  }%
  \vspace{0.3ex}%
}

% 技能胶囊标签 (Pill Tag)
\newcommand{\cvtag}[1]{%
  \tikz[baseline=(tag.base)]
    \node[anchor=text, rounded corners=3pt, fill=TagBackground, draw=TagBorder, inner sep=3pt, outer sep=1pt] (tag) {%
      \footnotesize\color{emphasis}#1%
    };%
  \hspace{1pt}%
}

% 紧凑列表样式
\setlist[itemize]{leftmargin=1.2em, itemsep=0.1ex, topsep=0.2ex, parsep=0ex}

\pagestyle{empty}
