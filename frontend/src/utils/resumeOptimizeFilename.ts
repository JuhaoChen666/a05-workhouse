/** 与 PDF 同源命名规则，扩展名固定为 .md（用于导出为 Markdown 时上传/下载） */
export function buildOptimizedResumeMarkdownFilename(original: string): string {
  const name = (original || '简历').trim() || '简历';
  const i = name.lastIndexOf('.');
  const stem = i > 0 ? name.slice(0, i) : name;
  return `${stem}（优化版）.md`;
}

/** 优化结果为 PDF 时使用：主文件名 +「（优化版）」+ .pdf */
export function buildOptimizedResumePdfFilename(original: string): string {
  const name = (original || '简历').trim() || '简历';
  const i = name.lastIndexOf('.');
  const stem = i > 0 ? name.slice(0, i) : name;
  return `${stem}（优化版）.pdf`;
}
