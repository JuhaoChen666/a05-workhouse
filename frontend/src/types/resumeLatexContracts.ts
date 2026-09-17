/**
 * Phase 0: 个人经历库与基于 LaTeX 的 JD 定制简历系统 - 前端类型契约
 * 对应 docs/specs/resume_latex_phase0_technical_contracts.md 规范
 */

export type ExperienceType = 'CERTIFICATE' | 'COMPETITION_AWARD' | 'PROJECT' | 'WORK' | 'SKILL'

export interface BaseExperienceItem {
  type: ExperienceType
  title: string
  start_date?: string | null // YYYY-MM
  end_date?: string | null   // YYYY-MM or 'present'
  tags: string[]
  is_archived: boolean
  sort_order?: number
  source_type?: 'MANUAL' | 'PDF_IMPORT'
  source_resume_id?: number | null
  source_locator?: Record<string, unknown>
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
  issue_date: string
  certificate_no?: string
  category?: string
  description?: string
}

export interface CompetitionAwardItem extends BaseExperienceItem {
  type: 'COMPETITION_AWARD'
  award_level: string
  award_date: string
  organization?: string
  rank?: string
  description?: string
}

export interface ProjectItem extends BaseExperienceItem {
  type: 'PROJECT'
  role: string
  project_url?: string
  tech_stack: string[]
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
  entry_file: string
  supported_languages: Array<"zh" | "en">
  [key: string]: unknown
  engine: 'xelatex' | 'pdflatex'
  cjk_package: string
  recommended_pages: number[]
  supports_avatar: boolean
  default_avatar_style: string
  supported_sections: string[]
}

export interface ResumeGenerationRequest {
  jd_source_type: 'TEXT' | 'JOB_ID'
  jd_text?: string
  job_id?: string
  template_id: string
  target_pages: 1 | 2
  language: 'zh' | 'en'
  show_avatar: boolean
  selected_item_ids?: string[] | null
  ai_recommendation_mode: 'MANUAL_ONLY' | 'JD_AUTO_SELECT_AND_TAILOR'
}

export interface AITailoredBulletTrace {
  source_item_id: string
  original_bullet: string
  tailored_bullet: string
  keywords_matched: string[]
}

export interface ResumeGenerationJob {
  job_id: string
  status: 'PENDING' | 'PROCESSING' | 'COMPILED' | 'FAILED'
  progress_percentage: number
  pdf_download_url?: string
  latex_source_url?: string
  compile_error_message?: string
  traces: AITailoredBulletTrace[]
  created_at: string
}

export interface ExperienceItemResponse {
  id: string
  user_id: number
  type: ExperienceType
  title: string
  start_date: string | null
  end_date: string | null
  tags: string[]
  attributes: Record<string, unknown>
  is_archived: boolean
  sort_order: number
  revision: number
  source_type: "MANUAL" | "PDF_IMPORT"
  source_resume_id: number | null
  source_locator: Record<string, unknown>
  created_at: string
  updated_at: string
}
