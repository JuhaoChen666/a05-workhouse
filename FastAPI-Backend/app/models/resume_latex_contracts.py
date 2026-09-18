"""
Phase 0: 个人经历库与基于 LaTeX 的 JD 定制简历系统 - 数据契约定义
依据 docs/specs/resume_latex_phase0_technical_contracts.md 规范制定
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
import re


class ExperienceTypeEnum(str, Enum):
    """五类经历枚举分类"""
    CERTIFICATE = "CERTIFICATE"                 # 证书/知识产权
    COMPETITION_AWARD = "COMPETITION_AWARD"     # 比赛获奖/荣誉
    PROJECT = "PROJECT"                         # 项目经历
    WORK = "WORK"                               # 工作/实习经历
    SKILL = "SKILL"                             # 专业技能/技术栈归类


class BaseExperienceItem(BaseModel):
    """所有经历条目的通用基础字段"""
    model_config = ConfigDict(extra="forbid")
    type: ExperienceTypeEnum = Field(..., description="经历枚举分类")
    title: str = Field(..., min_length=1, max_length=200, description="经历主标题（项目名/公司名/比赛名/证书名/技能分类名）")
    start_date: Optional[str] = Field(None, description="开始日期 (格式: YYYY-MM)")
    end_date: Optional[str] = Field(None, description="结束年月；null=未提供，present=持续中")
    tags: List[str] = Field(default_factory=list, description="技术标签/关键词列表")
    is_archived: bool = Field(False, description="是否归档")
    sort_order: int = Field(0, ge=0)
    source_type: Literal["MANUAL", "PDF_IMPORT", "MARKDOWN_IMPORT"] = "MANUAL"
    source_resume_id: Optional[int] = Field(None, gt=0)
    source_locator: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("start_date", "end_date", "issue_date", "award_date", check_fields=False)
    @classmethod
    def valid_month(cls, value, info):
        if value is None or (info.field_name == "end_date" and value == "present"):
            return value
        if not re.fullmatch(r"[1-9][0-9]{3}-(0[1-9]|1[0-2])", value):
            raise ValueError("expected YYYY-MM; only end_date allows present")
        return value

    @model_validator(mode="after")
    def consistent_fields(self):
        if self.start_date and self.end_date not in (None, "present") and self.end_date < self.start_date:
            raise ValueError("end_date precedes start_date")
        if self.source_type == "MANUAL" and (self.source_resume_id or self.source_locator):
            raise ValueError("manual entry cannot claim PDF provenance")
        return self


# ==========================================
# 五类经历专用输入模型 (Item Create/Update)
# ==========================================

class SkillItemCreate(BaseExperienceItem):
    """专业技能分类与技术栈"""
    type: Literal[ExperienceTypeEnum.SKILL] = ExperienceTypeEnum.SKILL
    category: str = Field(..., max_length=100, description="技能分类名称，如: 后端开发、前端工程、云原生与架构")
    skills: List[str] = Field(..., min_length=1, description="该分类包含的具体技术栈列表，如: ['Go', 'Python', 'FastAPI', 'Docker']")
    proficiency: Optional[str] = Field(None, max_length=50, description="熟练度级别，如: 精通/熟练/掌握")
    description: Optional[str] = Field(None, description="补充说明或核心技术实践年限")


class CertificateItemCreate(BaseExperienceItem):
    """证书与知识产权"""
    type: Literal[ExperienceTypeEnum.CERTIFICATE] = ExperienceTypeEnum.CERTIFICATE
    authority: Optional[str] = Field(None, max_length=150, description="颁发机构/认证单位")
    issue_date: str = Field(..., description="获得年月 (格式: YYYY-MM)")
    certificate_no: Optional[str] = Field(None, max_length=100, description="证书编号/专利号")
    category: Optional[str] = Field(None, max_length=50, description="分类 (资格认证/外语/专利/软著)")
    description: Optional[str] = Field(None, description="证书/知识产权详细说明")


class CompetitionAwardItemCreate(BaseExperienceItem):
    """比赛获奖与荣誉"""
    type: Literal[ExperienceTypeEnum.COMPETITION_AWARD] = ExperienceTypeEnum.COMPETITION_AWARD
    award_level: str = Field(..., max_length=100, description="奖项等级 (如: 国家一等奖、省级金奖)")
    award_date: str = Field(..., description="获奖年月 (格式: YYYY-MM)")
    organization: Optional[str] = Field(None, max_length=150, description="主办单位")
    rank: Optional[str] = Field(None, max_length=50, description="具体名次或队长/角色")
    description: Optional[str] = Field(None, description="比赛项目说明与参赛成果")


class ProjectItemCreate(BaseExperienceItem):
    """项目经历"""
    type: Literal[ExperienceTypeEnum.PROJECT] = ExperienceTypeEnum.PROJECT
    role: str = Field(..., max_length=100, description="担任角色 (如: 后端核心研发、架构师)")
    project_url: Optional[str] = Field(None, max_length=255, description="开源或演示链接")
    tech_stack: List[str] = Field(default_factory=list, description="技术栈清单")
    description: Optional[str] = Field(None, description="项目简要背景概述")
    bullets: List[str] = Field(..., min_length=1, description="核心亮点与产出 (STAR法则)")


class WorkItemCreate(BaseExperienceItem):
    """工作与实习经历"""
    type: Literal[ExperienceTypeEnum.WORK] = ExperienceTypeEnum.WORK
    department: Optional[str] = Field(None, max_length=100, description="所在部门/业务线")
    role: str = Field(..., max_length=100, description="职位名称")
    city: Optional[str] = Field(None, max_length=50, description="工作所在城市")
    bullets: List[str] = Field(..., min_length=1, description="核心职责与量化业务成果")


class ExperienceItemResponse(BaseModel):
    """经历条目统一出参"""
    id: str
    user_id: int
    type: ExperienceTypeEnum
    title: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    revision: int
    sort_order: int = 0
    source_type: Literal["MANUAL", "PDF_IMPORT", "MARKDOWN_IMPORT"] = "MANUAL"
    source_resume_id: Optional[int] = None
    source_locator: Dict[str, Any] = Field(default_factory=dict)
    is_archived: bool = False
    attributes: Dict[str, Any] = Field(default_factory=dict, description="对应分类的特有属性字典")
    created_at: datetime
    updated_at: datetime


# ==========================================
# LaTeX 模板与生成任务契约
# ==========================================

class ResumeTemplateMetadata(BaseModel):
    """LaTeX 模板元数据"""
    model_config = ConfigDict(extra="allow")
    id: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    name: str = Field(..., description="模板展示名称")
    version: str = Field("1.0.0", min_length=1, max_length=32, pattern=r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?$")
    protocol_version: Optional[Literal["1.0", "1.1"]] = None
    entry_file: str = "resume.tex.j2"
    supported_languages: List[Literal["zh", "en"]] = Field(default_factory=lambda: ["zh"], min_length=1)
    engine: str = Field("xelatex", description="编译引擎，如 xelatex")
    cjk_package: str = Field("xeCJK", description="中文字体处理宏包")
    recommended_pages: List[Literal[1, 2]] = Field(default_factory=lambda: [1], min_length=1)
    supports_avatar: bool = Field(True, description="是否支持证件照头像")
    default_avatar_style: str = Field("tikz_overlay_top_right", description="头像定位方式")
    supported_sections: List[str] = Field(..., description="支持的简历版块列表")
    placeholders: Dict[str, Any] = Field(..., description="固定模块占位符声明")


class ResumeGenerationRequest(BaseModel):
    """简历生成任务请求契约"""
    model_config = ConfigDict(extra="forbid")
    jd_source_type: Literal["TEXT", "JOB_ID"] = "TEXT"
    jd_text: Optional[str] = Field(None, description="原始 JD 文本内容")
    job_id: Optional[str] = Field(None, description="关联系统内岗位库的主键ID")
    template_id: str = Field("tpl-billryan-classic", description="选用的 LaTeX 模板标识")
    template_version: str | None = Field(None, min_length=1, max_length=32)
    target_pages: int = Field(1, ge=1, le=2, description="目标页数限制 (1 或 2，MVP 默认 1)")
    language: Literal["zh", "en"] = "zh"
    show_avatar: bool = Field(True, description="是否插入证件照")
    personal_info: dict[str, Any] = Field(default_factory=dict)
    selected_item_ids: Optional[List[str]] = Field(None, description="用户显式勾选的经历ID，为空则由AI全权推荐")
    ai_recommendation_mode: Literal["MANUAL_ONLY", "JD_AUTO_SELECT_AND_TAILOR"] = Field(
        "JD_AUTO_SELECT_AND_TAILOR",
        description="推荐模式: MANUAL_ONLY | JD_AUTO_SELECT_AND_TAILOR"
    )

    @model_validator(mode="after")
    def valid_selection(self):
        if self.jd_source_type == "TEXT":
            if not self.jd_text or not self.jd_text.strip() or self.job_id is not None:
                raise ValueError("TEXT requires JD text and no job_id")
        elif not self.job_id or not self.job_id.strip() or self.jd_text is not None:
            raise ValueError("JOB_ID requires job_id; JD is resolved by server")
        if self.selected_item_ids is not None and len(set(self.selected_item_ids)) != len(self.selected_item_ids):
            raise ValueError("duplicate experience selection")
        if len(self.personal_info) > 32:
            raise ValueError("personal_info has too many fields")
        return self


class AITailoredBulletTrace(BaseModel):
    """AI 润色生成的单条 Bullet 溯源快照"""
    source_item_id: str = Field(..., description="来源个人经历条目 ID")
    original_bullet: str = Field(..., description="原始经历条目文本")
    tailored_bullet: str = Field(..., description="针对 JD 润色后的文本")
    keywords_matched: List[str] = Field(default_factory=list, description="与目标 JD 命中的关键词")


class ResumeGenerationJobResponse(BaseModel):
    """简历生成异步任务响应状态"""
    job_id: str
    document_id: Optional[str] = None
    status: str = Field(..., description="PENDING | PROCESSING | WAITING_REVIEW | COMPILED | FAILED")
    progress_percentage: int = Field(0, ge=0, le=100)
    pdf_download_url: Optional[str] = None
    latex_source_url: Optional[str] = None
    compile_error_message: Optional[str] = None
    compile_error_location: Optional[str] = None
    stage: str = "PENDING"
    retryable: bool = False
    recommendation: Optional[dict[str, Any]] = None
    result_metadata: Optional[dict[str, Any]] = None
    review_plan: Optional[dict[str, Any]] = None
    review_decision: Optional[dict[str, Any]] = None
    traces: List[AITailoredBulletTrace] = Field(default_factory=list)
    created_at: datetime
