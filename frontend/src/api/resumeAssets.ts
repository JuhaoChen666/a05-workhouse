import { INTERVIEW_API_ORIGIN } from './request';

export function buildInterviewAssetUrl(path: string) {
  if (/^https?:\/\//i.test(path)) return path;
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const sameOrigin = typeof window !== 'undefined' ? window.location.origin : '';
  const base = INTERVIEW_API_ORIGIN || sameOrigin;
  return `${base}${normalizedPath}`;
}
