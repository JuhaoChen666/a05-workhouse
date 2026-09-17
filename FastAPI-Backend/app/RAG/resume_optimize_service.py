import asyncio
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import AsyncSessionLocal
from app.models.session_models import ResumeOptimizationModel
from app.llm.deepseek import DeepSeek_LLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 统一定义专属的简历优化模型链 Prompt
optimize_prompt = ChatPromptTemplate.from_template("""
你是一位专门帮助求职者拿到心仪技术 Offer 的资深 HR 兼技术面试官。
这是一份尚未经过任何润色的原始简历提取文本。请你对其进行全方位的排版、措辞优化、和技术亮点提炼。

【优化严格要求】
1. **纯粹的 Markdown 格式输出**：不要说任何客套话，不要包含诸如 ```markdown 的代码块前后缀包裹，直接开始输出文档内容。使用清晰的结构（例如：个人基本信息、求职意向、论文、专业技能、工作经验/项目经验、教育背景）。
2. **STAR法则精修**：对用户的每一段经历使用STAR法则（情境、任务、行动、结果）进行重写。
3. **排版以及格式**：请把输出的页码控制在2页以内,确保内容清晰,易读。2页是简历的黄金页码，最好不要超过。证书内容部分请放在荣誉上面,排版不要过于紧凑,保持松弛能让面试官更加放松。
4. **增加技术强动词与量化结果**：例如将“做了个功能”改为“主导设计并实现了XXX模块，系统吞吐量提升了20%，有效降低了服务器负载”。
5. 目标岗位参考：{target_job}
6. **精准优化**：请根据目标岗位要求，对简历进行精准优化，突出与目标岗位最相关的经历和技能。

原始简历内容如下：
---
{resume_text}
---
""")

class ResumeOptimizeService:
    
    @staticmethod
    async def optimize_resume_task(session_id: str, original_text: str, target_job: str = "IT研发工程师"):
        """
        异步后台执行的 LCEL 优化任务。
        会在流式获取模型回复的同时，实时将估算的进度百分比更新至 MySQL。
        """
        # 第一步：标记为解析与大模型初始化状态（10%）
        async with AsyncSessionLocal() as db_session:
            opt_record = await db_session.get(ResumeOptimizationModel, session_id)
            if not opt_record:
                return
            opt_record.status = "processing"
            opt_record.progress = 10
            await db_session.commit()
            
        try:
            chain = optimize_prompt | DeepSeek_LLM | StrOutputParser()
            
            optimized_result = ""
            chunk_count = 0
            
            # 开启异步流式大模型生成
            async for chunk in chain.astream({
                "resume_text": original_text,
                "target_job": target_job
            }):
                optimized_result += chunk
                chunk_count += 1
                
                # 每收到 15 个 chunk（分词片），向数据库提交一次进度提升，以此模拟连贯的实时进度条
                if chunk_count % 15 == 0:
                    # 进度模型：10% 出发，根据块数平滑增长到最高 95%，直到最后 100% 收尾
                    current_est = min(95, 10 + int(chunk_count / 4))
                    
                    async with AsyncSessionLocal() as db_session:
                        opt = await db_session.get(ResumeOptimizationModel, session_id)
                        if opt and opt.progress < current_est:
                            opt.progress = current_est
                            await db_session.commit()
            
            # 全部生成完成，把最终生成的 Markdown 落库，进度打满 100%
            async with AsyncSessionLocal() as db_session:
                opt_record = await db_session.get(ResumeOptimizationModel, session_id)
                if opt_record:
                    opt_record.optimized_text = optimized_result
                    opt_record.progress = 100
                    opt_record.status = "completed"
                    await db_session.commit()
                    
        except Exception as e:
            print(f"[简历优化 LCEL] 处理运行失败: session_id={session_id}, error={str(e)}")
            async with AsyncSessionLocal() as db_session:
                opt_record = await db_session.get(ResumeOptimizationModel, session_id)
                if opt_record:
                    opt_record.progress = 0
                    opt_record.status = "failed"
                    await db_session.commit()
