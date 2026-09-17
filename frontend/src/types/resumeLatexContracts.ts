/**
 * Phase 0: 个人经历库与基于 LaTeX 的 JD 定制简历系统 - 前端类型契约
 * 对应 docs/specs/resume_latex_phase0_technical_contracts.md 规范
 */

export type ExperienceType = 'CERTIFICATE' | 'COMPETITION_AWARD' | 'PROJECT' | 'WORK' | 'SKILL'

export interface BaseExperienceItem {
  id?: string
  type: ExperienceType
  title: string
  startDate?: string // YYYY-MM
  endDate?: string   // YYYY-MM or 'present'
  tags: string[]
  isArchived: boolean
  createdAt?: string
  updatedAt?: string
}

export interface SkillItem extends BaseExperienceItem {
  type: 'SKILL'
  category: string   // 技能分类，如：后端开发、前端工程、云原生与微服务
  skills: string[]   // 技术栈清单，如：['Go', 'Python', 'FastAPI', 'Docker']
  proficiency?: string // 熟练度，如：精通/熟练/掌握
  description?: string // 补充说明
}

export interface CertificateItem extends BaseExperienceItem {
  type: 'CERTIFICATE'
  authority?: string
  issueDate: string
  certificateNo?: string
  category?: string
  description?: string
}

export interface CompetitionAwardItem extends BaseExperienceItem {
  type: 'COMPETITION_AWARD'
  awardLevel: string
  awardDate: string
  organization?: string
  rank?: string
  description?: string
}

export interface ProjectItem extends BaseExperienceItem {
  type: 'PROJECT'
  role: string
  projectUrl?: string
  techStack: string[]
  description?: string
  bullets: string[]
}

export interface WorkItem extends BaseExperienceItem {
  type: 'WORK'
  department?: string
  role: string
  city?: string
  bullets: string[]
}

export type ExperienceItem = CertificateItem | CompetitionAwardItem | ProjectItem | WorkItem | SkillItem

export interface ResumeTemplateMetadata {
  id: string
  name: string
  version: string
  engine: 'xelatex' | 'pdflatex'
  cjkPackage: string
  recommendedPages: number[]
  supportsAvatar: boolean
  defaultAvatarStyle: string
  supportedSections: string[]
}

export interface ResumeGenerationRequest {
  jdSourceType: 'TEXT' | 'JOB_ID'
  jdText?: string
  jobId?: string
  templateId: string
  targetPages: 1 | 2
  language: 'zh' | 'en'
  showAvatar: boolean
  selectedItemIds?: string[]
  aiRecommendationMode: 'MANUAL_ONLY' | 'JD_AUTO_SELECT_AND_TAILOR'
}

export interface AITailoredBulletTrace {
  sourceItemId: string
  originalBullet: string
  tailoredBullet: string
  keywordsMatched: string[]
}

export interface ResumeGenerationJob {
  jobId: string
  status: 'PENDING' | 'PROCESSING' | 'COMPILED' | 'FAILED'
  progressPercentage: number
  pdfDownloadUrl?: string
  latexSourceUrl?: string
  compileErrorMessage?: string
  traces: AITailoredBulletTrace[]
  createdAt: string
}
