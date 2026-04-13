/**
 * 将岗位详情映射为面试/押题接口使用的 position 标识（如 backend_engineer）。
 * 若后端已返回 snake_case，则原样使用。
 */
export function resolvePositionSlug(params: { type?: string; name?: string; jobId: number }): string {
  const rawType = String(params.type || '').trim();
  if (/^[a-z][a-z0-9_]*$/.test(rawType)) {
    return rawType;
  }

  const cnMap: Record<string, string> = {
    后端: 'backend_engineer',
    后端开发: 'backend_engineer',
    前端: 'frontend_engineer',
    前端开发: 'frontend_engineer',
    算法: 'algorithm_engineer',
    算法工程师: 'algorithm_engineer',
    数据: 'data_engineer',
    大数据: 'data_engineer',
    运维: 'devops_engineer',
    测试: 'qa_engineer',
    客户端: 'mobile_engineer',
    Android: 'android_engineer',
    iOS: 'ios_engineer',
    全栈: 'fullstack_engineer',
  };
  if (rawType && cnMap[rawType]) {
    return cnMap[rawType];
  }

  const n = String(params.name || '');
  if (/后端|Java|Go|服务端|Spring|微服务/.test(n)) return 'backend_engineer';
  if (/前端|React|Vue|TypeScript|Web/.test(n)) return 'frontend_engineer';
  if (/算法|机器学习|深度学习|NLP|CV/.test(n)) return 'algorithm_engineer';
  if (/数据|数仓|ETL|Spark|Flink/.test(n)) return 'data_engineer';
  if (/运维|SRE|K8s|Kubernetes/.test(n)) return 'devops_engineer';
  if (/测试|QA|质量/.test(n)) return 'qa_engineer';

  return `position_${params.jobId}`;
}
