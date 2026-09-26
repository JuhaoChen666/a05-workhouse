import type { UserInfo } from '@/types/auth';

export interface ResumeEducationEntry {
  school: string;
  major: string;
  degree: string;
  date_range: string;
  gpa?: string;
}

export interface ResumePersonalProfile {
  name: string;
  title: string;
  phone: string;
  email: string;
  city: string;
  github: string;
  education: ResumeEducationEntry[];
}

const STORAGE_KEY_PREFIX = 'resume.personalProfile.v1';

const defaultEducation = (): ResumeEducationEntry => ({
  school: '',
  major: '',
  degree: '',
  date_range: '',
  gpa: '',
});

export function emptyEducationEntry() {
  return defaultEducation();
}

function storageKey(user?: Pick<UserInfo, 'id' | 'username'> | null) {
  const id = user?.id || user?.username || 'anonymous';
  return `${STORAGE_KEY_PREFIX}.${id}`;
}

function normalizeEducation(value: unknown): ResumeEducationEntry[] {
  if (!Array.isArray(value)) return [];
  return value.map((entry) => {
    const row = entry && typeof entry === 'object' ? entry as Record<string, unknown> : {};
    return {
      school: String(row.school || ''),
      major: String(row.major || ''),
      degree: String(row.degree || ''),
      date_range: String(row.date_range || ''),
      gpa: String(row.gpa || ''),
    };
  });
}

export function normalizeResumePersonalProfile(
  raw: unknown,
  user?: Pick<UserInfo, 'username' | 'email'> | null,
): ResumePersonalProfile {
  const source = raw && typeof raw === 'object' ? raw as Record<string, unknown> : {};
  return {
    name: String(source.name || source.username || user?.username || ''),
    title: String(source.title || ''),
    phone: String(source.phone || ''),
    email: String(source.email || user?.email || ''),
    city: String(source.city || ''),
    github: String(source.github || ''),
    education: normalizeEducation(source.education),
  };
}

export function loadResumePersonalProfile(user?: UserInfo | null): ResumePersonalProfile {
  try {
    const saved = localStorage.getItem(storageKey(user));
    return normalizeResumePersonalProfile(saved ? JSON.parse(saved) : null, user);
  } catch {
    return normalizeResumePersonalProfile(null, user);
  }
}

export function saveResumePersonalProfile(profile: ResumePersonalProfile, user?: UserInfo | null) {
  localStorage.setItem(storageKey(user), JSON.stringify(normalizeResumePersonalProfile(profile, user)));
}

export function resumeProfileMissingFields(profile: ResumePersonalProfile) {
  const missing: string[] = [];
  if (!profile.name.trim()) missing.push('姓名');
  if (!profile.title.trim()) missing.push('求职方向');
  if (!profile.phone.trim()) missing.push('电话');
  if (!profile.email.trim()) missing.push('邮箱');
  if (!profile.city.trim()) missing.push('城市');

  const education = profile.education.filter((entry) =>
    Object.values(entry).some((value) => String(value || '').trim()),
  );
  if (!education.length) {
    missing.push('教育经历');
  } else {
    education.forEach((entry, index) => {
      const prefix = `教育经历 ${index + 1}`;
      if (!entry.school.trim()) missing.push(`${prefix} 学校`);
      if (!entry.major.trim()) missing.push(`${prefix} 专业`);
      if (!entry.degree.trim()) missing.push(`${prefix} 学历`);
      if (!entry.date_range.trim()) missing.push(`${prefix} 就读年月`);
    });
  }
  return missing;
}
