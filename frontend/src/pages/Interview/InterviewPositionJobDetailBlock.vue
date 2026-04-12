<template>
  <div class="job-detail-block">
    <el-empty v-if="!job" description="请搜索并选择工作岗位" :image-size="72" />
    <div v-else-if="loading" class="selected-job-card detail-loading">岗位详情加载中...</div>
    <div v-else-if="error" class="selected-job-card detail-error">{{ error }}</div>
    <div v-else class="selected-job-card">
      <div class="header-row">
        <h4>{{ detail?.name || job.name }}</h4>
      </div>
      <p class="job-time" v-if="detail?.updateTime">更新时间：{{ detail?.updateTime }}</p>

      <div class="salary-block" v-if="showSalary">
        <h5>薪资范围</h5>
        <ul>
          <li v-if="detail?.salaryJunior"><span>初级</span><b>{{ detail?.salaryJunior }}</b></li>
          <li v-if="detail?.salaryMid"><span>中级</span><b>{{ detail?.salaryMid }}</b></li>
          <li v-if="detail?.salarySenior"><span>高级</span><b>{{ detail?.salarySenior }}</b></li>
          <li v-if="detail?.salaryExpert"><span>专家</span><b>{{ detail?.salaryExpert }}</b></li>
        </ul>
      </div>

      <div class="text-block">
        <h5>技能要求</h5>
        <div v-if="skillRequirementLines.length" class="skill-body">
          <ul class="skill-requirements-list">
            <li v-for="(line, i) in skillRequirementLines" :key="i" class="skill-item">{{ line }}</li>
          </ul>
        </div>
        <p v-else class="job-content job-content--empty">暂无技能要求</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { HotJobItem } from '@/api/jobs';

const props = defineProps<{
  job: HotJobItem | undefined;
  loading: boolean;
  error: string;
  detail: {
    name: string;
    type: string;
    jobContent: string;
    companyName: string;
    responsibility: string;
    skillRequirements: string;
    salaryJunior: string;
    salaryMid: string;
    salarySenior: string;
    salaryExpert: string;
    updateTime: string;
  } | null;
}>();

const showSalary = computed(() => {
  const d = props.detail;
  if (!d) return false;
  return Boolean(d.salaryJunior || d.salaryMid || d.salarySenior || d.salaryExpert);
});

/** 将技能要求长文本拆成条目，便于列表展示 */
const skillRequirementLines = computed(() => {
  const raw = String(
    props.detail?.skillRequirements?.trim() || props.detail?.jobContent?.trim() || ''
  );
  if (!raw) return [];

  const stripEnumPrefix = (s: string) =>
    s.replace(/^\s*[\d０-９]+[、.．]\s*/, '').trim();

  const lines: string[] = [];

  for (const block of raw.split(/\r?\n+/)) {
    const t = block.trim();
    if (!t) continue;

    const parts = t.split(/[；;]+/).map((p) => stripEnumPrefix(p.trim())).filter(Boolean);
    if (parts.length > 1) {
      lines.push(...parts);
      continue;
    }

    const one = stripEnumPrefix(parts[0] || t);
    if (!one) continue;

    const splitNum = one
      .split(/(?=[\d０-９]+[、.．])/)
      .map((s) => stripEnumPrefix(s.trim()))
      .filter(Boolean);
    if (splitNum.length > 1) {
      lines.push(...splitNum);
      continue;
    }

    lines.push(one);
  }

  return lines;
});
</script>

<style scoped>
.detail-title {
  margin: 0 0 8px;
}
.selected-job-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 14px;
  background: #fff;
  max-height: 340px;
  overflow-y: auto;
}
.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.header-row h4 {
  margin: 0;
  font-size: 16px;
}
.job-time {
  margin: 0 0 10px;
  color: #9ca3af;
  font-size: 12px;
}
.salary-block {
  margin-bottom: 12px;
  border: 1px solid #ede9fe;
  background: #faf5ff;
  border-radius: 10px;
  padding: 10px 12px;
}
.salary-block h5 {
  margin: 0 0 8px;
  font-size: 13px;
  color: #374151;
}
.text-block h5 {
  margin: 0 0 10px;
  font-size: 13px;
  color: #374151;
  font-weight: 600;
}
.salary-block ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 6px;
}
.salary-block li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
  color: #4b5563;
}
.salary-block li b {
  color: #111827;
  font-weight: 700;
}
.text-block {
  margin-bottom: 12px;
}
.skill-body {
  background: linear-gradient(180deg, #fafafa 0%, #f5f5f7 100%);
  border: 1px solid #ececf1;
  border-radius: 10px;
  padding: 12px 12px 12px 10px;
}
.skill-requirements-list {
  margin: 0;
  padding: 0;
  list-style: none;
}
.skill-item {
  position: relative;
  padding: 6px 0 6px 1.15em;
  margin: 0;
  color: #374151;
  font-size: 13px;
  line-height: 1.65;
  letter-spacing: 0.01em;
  border-bottom: 1px solid rgba(229, 231, 235, 0.85);
}
.skill-item:last-child {
  border-bottom: none;
  padding-bottom: 2px;
}
.skill-item:first-child {
  padding-top: 2px;
}
.skill-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.72em;
  width: 6px;
  height: 6px;
  border-radius: 2px;
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  flex-shrink: 0;
}
.job-content {
  margin: 0;
  color: #374151;
  line-height: 1.7;
  white-space: pre-wrap;
}
.job-content--empty {
  color: #9ca3af;
  font-size: 13px;
  padding: 10px 12px;
  background: #f9fafb;
  border-radius: 10px;
  border: 1px dashed #e5e7eb;
  text-align: center;
}
.detail-loading,
.detail-error {
  color: #6b7280;
  line-height: 1.7;
}
.detail-error {
  color: #b91c1c;
}

@media (max-width: 768px) {
  .selected-job-card {
    max-height: none;
  }
}
</style>
