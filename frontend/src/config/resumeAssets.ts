import { INTERVIEW_API_ORIGIN } from '@/api/request';

/** 已上传简历的静态访问根路径，与「我的简历」在线预览一致 */
export const RESUME_FILE_PUBLIC_BASE_URL = `${INTERVIEW_API_ORIGIN}/data/resumes/`;

/**
 * 将后端返回的简历路径规范成可访问的公开 URL。
 * 兼容：
 * - Windows 分隔符：resumes\abc.pdf
 * - 带前缀路径：/data/resumes/abc.pdf、resumes/abc.pdf
 * - 已经是完整地址：http(s)://host/data/resumes/abc.pdf
 */
export function buildResumeFilePublicUrl(fileKeyRaw: string): string {
  const raw = String(fileKeyRaw || '').trim();
  if (!raw) return '';

  const [beforeQuery = ''] = raw.split('?');
  const [noQuery = ''] = beforeQuery.split('#');
  const noOrigin = noQuery.replace(/^https?:\/\/[^/]+/i, '');
  const slashNormalized = noOrigin.replace(/\\/g, '/');

  let relative = slashNormalized.replace(/^\/+/, '');
  relative = relative.replace(/^data\/resumes\/+/i, '');
  relative = relative.replace(/^resumes\/+/i, '');

  if (!relative) return '';
  return `${RESUME_FILE_PUBLIC_BASE_URL}${encodeURIComponent(relative)}`;
}
