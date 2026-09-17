"""
Phase 0: 个人经历库与基于 LaTeX 的 JD 定制简历系统 - 数据契约定义
依据 docs/specs/resume_latex_phase0_technical_contracts.md 规范制定
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExperienceTypeEnum(str, Enum):
    """五类经历枚举分类"""
    CERTIFICATE = "CERTIFICATE"                 # 证书/知识产权
    COMPETITION_AWARD = "COMPETITION_AWARD"     # 比赛获奖/荣誉
    PROJECT = "PROJECT"                         # 项目经历
    WORK = "WORK"                               # 工作/实习经历
    SKILL = "SKILL"                             # 专业技能/技术栈归类


class BaseExperienceItem(BaseModel):
    """所有经历条目的通用基础字段"""
    id: Optional[str] = Field(None, description="经历条目唯一UUID")
    type: ExperienceTypeEnum = Field(..., description="经历枚举分类")
    title: str = Field(..., max_length=200, description="经历主标题（项目名/公司名/比赛名/证书名/技能分类名）")
    start_date: Optional[str] = Field(None, description="开始日期 (格式: YYYY-MM)")
    end_date: Optional[str] = Field(None, description="结束日期 (格式: YYYY-MM，为空或present表示至今)")
    tags: List[str] = Field(default_factory=list, description="技术标签/关键词列表")
    is_archived: bool = Field(False, description="是否归档")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")


# ==========================================
# 五类经历专用输入模型 (Item Create/Update)
# ==========================================

class SkillItemCreate(BaseExperienceItem):
    """专业技能分类与技术栈"""
    type: ExperienceTypeEnum = ExperienceTypeEnum.SKILL
    category: str = Field(..., max_length=100, description="技能分类名称，如: 后端开发、前端工程、云原生与架构")
    skills: List[str] = Field(..., min_items=1, description="该分类包含的具体技术栈列表，如: ['Go', 'Python', 'FastAPI', 'Docker']")
    proficiency: Optional[str] = Field(None, max_length=50, description="熟练度级别，如: 精通/熟练/掌握")
    description: Optional[str] = Field(None, description="补充说明或核心技术实践年限")


class CertificateItemCreate(BaseExperienceItem):
    """证书与知识产权"""
    type: ExperienceTypeEnum = ExperienceTypeEnum.CERTIFICATE
    authority: Optional[str] = Field(None, max_length=150, description="颁发机构/认证单位")
    issue_date: str = Field(..., description="获得年月 (格式: YYYY-MM)")
    certificate_no: Optional[str] = Field(None, max_length=100, description="证书编号/专利号")
    category: Optional[str] = Field(None, max_length=50, description="分类 (资格认证/外语/专利/软著)")
    description: Optional[str] = Field(None, description="证书/知识产权详细说明")


class CompetitionAwardItemCreate(BaseExperienceItem):
    """比赛获奖与荣誉"""
    type: ExperienceTypeEnum = ExperienceTypeEnum.COMPETITION_AWARD
    award_level: str = Field(..., max_length=100, description="奖项等级 (如: 国家一等奖、省级金奖)")
    award_date: str = Field(..., description="获奖年月 (格式: YYYY-MM)")
    organization: Optional[str] = Field(None, max_length=150, description="主办单位")
    rank: Optional[str] = Field(None, max_length=50, description="具体名次或队长/角色")
    description: Optional[str] = Field(None, description="比赛项目说明与参赛成果")


class ProjectItemCreate(BaseExperienceItem):
    """项目经历"""
    type: ExperienceTypeEnum = ExperienceTypeEnum.PROJECT
    role: str = Field(..., max_length=100, description="担任角色 (如: 后端核心研发、架构师)")
    project_url: Optional[str] = Field(None, max_length=255, description="开源或演示链接")
    tech_stack: List[str] = Field(default_factory=list, description="技术栈清单")
    description: Optional[str] = Field(None, description="项目简要背景概述")
    bullets: List[str] = Field(..., min_items=1, description="核心亮点与产出 (STAR法则)")


class WorkItemCreate(BaseExperienceItem):
    """工作与实习经历"""
    type: ExperienceTypeEnum = ExperienceTypeEnum.WORK
    department: Optional[str] = Field(None, max_length=100, description="所在部门/业务线")
    role: str = Field(..., max_length=100, description="职位名称")
    city: Optional[str] = Field(None, max_length=50, description="工作所在城市")
    bullets: List[str] = Field(..., min_items=1, description="核心职责与量化业务成果")


class ExperienceItemResponse(BaseModel):
    """经历条目统一出参"""
    id: str
    user_id: str
    type: ExperienceTypeEnum
    title: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    tags: List[str] = []
    is_archived: bool = False
    attributes: Dict[str, Any] = Field(default_factory=dict, description="对应分类的特有属性字典")
    created_at: datetime
    updated_at: datetime


# ==========================================
# LaTeX 模板与生成任务契约
# ==========================================

class ResumeTemplateMetadata(BaseModel):
    """LaTeX 模板元数据"""
    id: str = Field(..., description="模板唯一标识，如 tpl-billryan-classic")
    name: str = Field(..., description="模板展示名称")
    version: str = Field("1.0.0", description="语义化版本号")
    engine: str = Field("xelatex", description="编译引擎，如 xelatex")
    cjk_package: str = Field("xeCJK", description="中文字体处理宏包")
    recommended_pages: List[int] = Field([1], description="建议页数")
    supports_avatar: bool = Field(True, description="是否支持证件照头像")
    default_avatar_style: str = Field("tikz_overlay_top_right", description="头像定位方式")
    supported_sections: List[str] = Field(..., description="支持的简历版块列表")


class ResumeGenerationRequest(BaseModel):
    """简历生成任务请求契约"""
    jd_source_type: str = Field("TEXT", description="JD来源类型: TEXT 或 JOB_ID")
    jd_text: Optional[str] = Field(None, description="原始 JD 文本内容")
    job_id: Optional[str] = Field(None, description="关联系统内岗位库的主键ID")
    template_id: str = Field("tpl-billryan-classic", description="选用的 LaTeX 模板标识")
    target_pages: int = Field(1, ge=1, le=2, description="目标页数限制 (1 或 2，MVP 默认 1)")
    language: str = Field("zh", description="简历语言 (zh / en)")
    show_avatar: bool = Field(True, description="是否插入证件照")
    selected_item_ids: Optional[List[str]] = Field(None, description="用户显式勾选的经历ID，为空则由AI全权推荐")
    ai_recommendation_mode: str = Field(
        "JD_AUTO_SELECT_AND_TAILOR",
        description="推荐模式: MANUAL_ONLY | JD_AUTO_SELECT_AND_TAILOR"
    )


class AITailoredBulletTrace(BaseModel):
    """AI 润色生成的单条 Bullet 溯源快照"""
    source_item_id: str = Field(..., description="来源个人经历条目 ID")
    original_bullet: str = Field(..., description="原始经历条目文本")
    tailored_bullet: str = Field(..., description="针对 JD 润色后的文本")
    keywords_matched: List[str] = Field(default_factory=list, description="与目标 JD 命中的关键词")


class ResumeGenerationJobResponse(BaseModel):
    """简历生成异步任务响应状态"""
    job_id: str
    status: str = Field(..., description="PENDING | PROCESSING | COMPILED | FAILED")
    progress_percentage: int = Field(0, ge=0, le=100)
    pdf_download_url: Optional[str] = None
    latex_source_url: Optional[str] = None
    compile_error_message: Optional[str] = None
    traces: List[AITailoredBulletTrace] = []
    created_at: datetime
