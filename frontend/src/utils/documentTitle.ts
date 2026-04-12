import type { RouteLocationNormalized } from 'vue-router';
import { loadInterviewSetupDraft } from '@/pages/Interview/setupState';

/** 介绍页（落地页）与默认标签标题使用的站点名 */
export const DOCUMENT_TITLE_BRAND = '面智通途';

/**
 * 根据路由解析浏览器标题：
 * - 落地页：固定品牌名
 * - 面试设置 / 会话 / 评估：优先使用岗位/主题（query.jobName 或面试草稿中的岗位名）
 * - 其余：优先使用路由 meta.title
 */
export function resolveDocumentTitle(to: RouteLocationNormalized): string {
  const name = to.name as string | undefined;

  if (name === 'Landing') {
    return DOCUMENT_TITLE_BRAND;
  }

  if (name === 'InterviewSettings' || name === 'InterviewSession') {
    const fromQuery = String(to.query.jobName || '').trim();
    if (fromQuery) return fromQuery;
    if (name === 'InterviewSettings') {
      const draft = loadInterviewSetupDraft();
      const fromDraft = (draft.positionName || '').trim();
      if (fromDraft) return fromDraft;
      return '面试设置';
    }
    return '面试';
  }

  if (name === 'InterviewEvaluation') {
    const fromQuery = String(to.query.jobName || '').trim();
    if (fromQuery) return fromQuery;
    return '面试评估报告';
  }

  const fromMeta = [...to.matched]
    .reverse()
    .map((r) => r.meta?.title)
    .find((t) => typeof t === 'string' && t.trim()) as string | undefined;
  if (fromMeta) return fromMeta.trim();

  if (typeof name === 'string' && name.trim()) return name.trim();

  return DOCUMENT_TITLE_BRAND;
}
