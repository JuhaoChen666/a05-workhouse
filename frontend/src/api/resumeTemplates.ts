import { interviewRequest } from './request'
import type {
  ResumeTemplateDetail,
  ResumeTemplateSummary,
  TemplateCompatibilityRequest,
  TemplateCompatibilityResponse,
  TemplatePreviewRequest,
  TemplatePreviewResponse,
  TemplateValidationReport,
} from '@/types/resumeLatexContracts'

const templateVersionPath = (templateId: string, version: string) =>
  `/resume-templates/${encodeURIComponent(templateId)}/versions/${encodeURIComponent(version)}`

export function listResumeTemplatesApi(includeUnavailable = false) {
  return interviewRequest.get<ResumeTemplateSummary[]>('/resume-templates', {
    params: { include_unavailable: includeUnavailable },
  })
}

export function getResumeTemplateApi(templateId: string, version?: string) {
  return interviewRequest.get<ResumeTemplateDetail>(`/resume-templates/${encodeURIComponent(templateId)}`, {
    params: version ? { version } : undefined,
  })
}

export function getResumeTemplateVersionApi(templateId: string, version: string) {
  return interviewRequest.get<ResumeTemplateDetail>(templateVersionPath(templateId, version))
}

export function listResumeTemplateVersionsApi(templateId: string) {
  return interviewRequest.get<ResumeTemplateSummary[]>(
    `/resume-templates/${encodeURIComponent(templateId)}/versions`,
  )
}

export function validateResumeTemplateApi(templateId: string, version: string) {
  return interviewRequest.get<TemplateValidationReport>(`${templateVersionPath(templateId, version)}/validate`)
}

export function checkResumeTemplateCompatibilityApi(
  templateId: string,
  version: string,
  request: TemplateCompatibilityRequest,
) {
  return interviewRequest.post<TemplateCompatibilityResponse>(
    `${templateVersionPath(templateId, version)}/compatibility`,
    request,
  )
}

export function previewResumeTemplateApi(
  templateId: string,
  version: string,
  request: TemplatePreviewRequest,
) {
  return interviewRequest.post<TemplatePreviewResponse>(
    `${templateVersionPath(templateId, version)}/preview`,
    request,
  )
}
