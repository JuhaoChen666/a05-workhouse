\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{resume}[2026/09/17 An elegant Resume class for A05-Workhouse]
\LoadClass[11pt]{article}

% Disable indent globally
\setlength{\parindent}{0pt}

% Required packages
\RequirePackage{xltxtra}
\RequirePackage{xifthen}
\RequirePackage{hyperref}
\hypersetup{hidelinks}
\RequirePackage{url}
\urlstyle{tt}
\RequirePackage{fontawesome}
\RequirePackage{fontspec}

\RequirePackage[
	a4paper,
	left=0.75in,
	right=0.75in,
	top=0.65in,
	bottom=0.55in,
	nohead
]{geometry}

\RequirePackage{titlesec}
\RequirePackage{enumitem}
\setlist{noitemsep}
\setlist[itemize]{topsep=0.20em, leftmargin=1.2pc}
\setlist[enumerate]{topsep=0.20em, leftmargin=1.2pc}

\titleformat{\section}
  {\Large\bfseries\raggedright}
  {}{0em}
  {}
  [{\titlerule[0.8pt]}]
\titlespacing*{\section}{0pt}{1.2ex plus 0.5ex minus 0.2ex}{1.0ex plus 0.2ex}

\newcommand{\datedsubsection}[2]{%
  \par\vspace{0.4ex}%
  \textbf{#1} \hfill \textit{#2}%
  \par\vspace{0.2ex}%
}

\newcommand{\role}[2]{%
  {\small \textbf{#1} \hfill #2}%
  \par\vspace{0.1ex}%
}
