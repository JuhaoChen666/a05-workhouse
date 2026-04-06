<template>
  <div class="home-page">
    <div class="bg-pattern"></div>
    <div class="bg-layer"></div>

    <!-- Banner -->
    <div class="banner">
      <div class="banner-content">
        <h1 class="fade-in-up title">
          AI 模拟面试平台<br />
          <span class="highlight">开启你的高薪之路</span>
        </h1>
        <p class="fade-in-up delay-1 subtitle">智能面试练习，助力求职进阶，掌控真实面试节奏！</p>
        <div class="banner-actions fade-in-up delay-2">
          <div class="banner-search-wrap">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索心仪岗位，例如：前端开发、Java、算法工程师"
              class="banner-search-input"
              clearable
              size="large"
              @keyup.enter="goJobSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" size="large" class="banner-search-btn" @click="goJobSearch">
              搜索岗位
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 下方两栏：左侧热门岗位 | 右侧最近报告 -->
    <div class="main-content">
      <el-row :gutter="24" class="main-row">
        <el-col :span="16">
          <div class="section-header">
            <h2 class="section-title">热门岗位 <span>Hot Jobs</span></h2>
            <div class="section-decoration"></div>
          </div>
          <el-row :gutter="20" class="job-cards">
            <el-col v-for="j in hotJobs" :key="j.id" :span="12">
              <el-card shadow="hover" class="job-card fade-in-up" @click="goJobDetail(j.id)">
                <div class="job-card-header">
                  <span class="job-name">{{ j.name }}</span>
                  <span class="job-salary">
                    {{ formatSalaryRange(j.salaryMin, j.salaryMax) }}
                  </span>
                </div>
                <div class="company-name">
                  <img
                    v-if="j.companyLogo"
                    :src="`/img/${j.companyLogo}.ico`"
                    class="company-logo"
                    alt="company logo"
                  />
                  <span>{{ j.companyName }}</span>
                </div>
                <p class="job-desc">{{ (j.jobContent || '').slice(0, 65) }}...</p>
                <div class="job-card-footer">
                  <span class="detail-link">查看详情 <el-icon class="el-icon--right"><ArrowRight /></el-icon></span>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </el-col>
        <el-col :span="8">
          <div class="section-header">
            <h2 class="section-title">最近报告 <span>Latest Report</span></h2>
            <div class="section-decoration"></div>
          </div>
          <el-card v-loading="reportLoading" shadow="hover" class="report-card fade-in-up delay-1">
            <template v-if="latestReport">
              <div class="report-score-wrap">
                <div class="score-circle">
                  <span class="score-num">{{ latestReport.totalScore ?? '--' }}</span>
                  <span class="score-unit">分</span>
                </div>
                <div class="score-label">综合得分</div>
              </div>
              <p class="report-summary">{{ latestReport.summary || '暂无总结' }}</p>
              <div class="report-action">
                <button class="full-btn" @click="goReport">查看完整报告</button>
              </div>
            </template>
            <el-empty v-else description="暂无面试报告" :image-size="80" />
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 页尾 -->
    <div class="home-footer">
      <div class="home-footer-inner">
        <div class="logo">
          <el-icon class="logo-icon" style="margin-right: 4px;"><Platform /></el-icon>
          <span class="logo-text">AI 面试官</span>
        </div>
        <p class="home-footer-desc">本项目用于学习与演示，不代表真实招聘信息。</p>
        <div class="footer-copyright">© 2026 AI Interview Platform. All rights reserved.</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { Search, ArrowRight, Platform } from '@element-plus/icons-vue';
import { getHotJobsApi, formatSalaryRange, type HotJobItem } from '@/api/jobs';
import { getReportByRecordIdApi } from '@/api/report';
import { getInterviewRecordListApi } from '@/api/interview';

const router = useRouter();
const hotJobs = ref<HotJobItem[]>([]);
const reportLoading = ref(false);
const latestReport = ref<{ totalScore?: number; summary?: string } | null>(null);
const latestRecordId = ref<number | null>(null);
const searchKeyword = ref('');

function goJobDetail(id: number) {
  router.push({ name: 'JobDetail', params: { id: String(id) } });
}
function goReport() {
  if (latestRecordId.value) router.push({ name: 'ReportDetail', params: { id: String(latestRecordId.value) } });
}

// 从首页 banner 进入岗位搜索页
function goJobSearch() {
  router.push({
    name: 'JobSearch',
    query: {
      keyword: searchKeyword.value || undefined,
    },
  });
}

onMounted(async () => {
  try {
    const list = await getHotJobsApi({ limit: 6 });
    hotJobs.value = list ?? [];
  } catch {}

  reportLoading.value = true;
  try {
    const listRes = await getInterviewRecordListApi({ page: 1, pageSize: 1 });
    const first = (listRes.list ?? [])[0];
    if (first?.id) {
      latestRecordId.value = first.id;
      const rep = await getReportByRecordIdApi(first.id);
      if (rep?.content) {
        latestReport.value = {
          totalScore: rep.content.totalScore,
          summary: rep.content.summary,
        };
      }
    }
  } catch {
    latestReport.value = null;
  } finally {
    reportLoading.value = false;
  }
});
</script>

<style scoped>
.home-page {
  padding-bottom: 0;
  background-color: #fafafa;
  min-height: 100vh;
  color: #1a1a1a;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  overflow-x: hidden;
  position: relative;
}

/* --- Textured Background --- */
.bg-pattern {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  background-image: radial-gradient(#d1d5db 1px, transparent 1px);
  background-size: 24px 24px;
  opacity: 0.5;
  pointer-events: none;
}

.bg-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  pointer-events: none;
  background: radial-gradient(circle at 80% -10%, rgba(147, 51, 234, 0.15) 0%, transparent 50%),
              radial-gradient(circle at 20% 110%, rgba(59, 130, 246, 0.1) 0%, transparent 40%);
}

/* Banner Styles */
.banner {
  position: relative;
  z-index: 10;
  padding: 80px 24px 60px;
  text-align: center;
  margin-bottom: 20px;
}

.banner-content {
  position: relative;
  max-width: 800px;
  margin: 0 auto;
}

.title {
  font-size: 48px;
  line-height: 1.15;
  font-weight: 800;
  margin-bottom: 20px;
  letter-spacing: -1.5px;
  color: #111827;
}

.highlight {
  background: linear-gradient(135deg, #a855f7 0%, #7e22ce 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  display: inline-block;
  font-size: 36px;
  margin-top: 8px;
}

.subtitle {
  font-size: 18px;
  line-height: 1.6;
  color: #4b5563;
  margin-bottom: 40px;
  font-weight: 400;
}

.banner-actions {
  display: flex;
  justify-content: center;
}

.banner-search-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  max-width: 640px;
  background: #ffffff;
  padding: 8px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
}

.banner-search-input :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: none;
  height: 48px;
}

.banner-search-btn {
  white-space: nowrap;
  height: 48px;
  border-radius: 8px;
  font-weight: 600;
  padding: 0 32px;
  background: linear-gradient(180deg, #4877b8, #000000);
  border: 1px solid #000000;
  color: #ffffff;
  transition: all 0.2s ease;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.1);
}

.banner-search-btn:hover, .banner-search-btn:focus {
  background: #333333;
  border-color: #333333;
  transform: translateY(-2px);
  box-shadow: 0 8px 15px rgba(0,0,0,0.15);
  color: #ffffff;
}

/* Main Content Styles */
.main-content {
  position: relative;
  z-index: 10;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

.section-header {
  margin-bottom: 30px;
  position: relative;
}

.section-title {
  font-size: 24px;
  font-weight: 800;
  color: #111827;
  margin: 0;
  display: flex;
  align-items: baseline;
  gap: 12px;
  letter-spacing: -0.5px;
}

.section-title span {
  font-size: 14px;
  color: #6b7280;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.section-decoration {
  width: 48px;
  height: 4px;
  background: linear-gradient(90deg, #a855f7, #3b82f6);
  border-radius: 2px;
  margin-top: 12px;
}

/* Job Cards Styles */
.job-cards {
  margin-bottom: 40px;
}

.job-card {
  cursor: pointer;
  margin-bottom: 24px;
  position: relative;
  background: linear-gradient(145deg, #ffffff 0%, #f9fafb 100%);
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02), inset 0 1px 0 rgba(255, 255, 255, 1);
  overflow: hidden;
  height: 270px;
}

.job-card :deep(.el-card__body) {
  padding: 24px;
  height: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

.job-card::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #a855f7, #3b82f6);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.job-card:hover {
  border-color: rgba(168, 85, 247, 0.3);
  box-shadow: 0 20px 40px -10px rgba(147, 51, 234, 0.1), inset 0 1px 0 rgba(255, 255, 255, 1);
  transform: translateY(-6px);
}
.job-card:hover::after {
  opacity: 1;
}

.job-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.job-name {
  font-size: 19px;
  font-weight: 800;
  color: #111827;
  transition: color 0.3s;
}

.job-card:hover .job-name {
  color: #9333ea;
}

.company-name {
  font-size: 13px;
  color: #4b5563;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  background: #f3f4f6;
  padding: 6px 12px;
  border-radius: 6px;
  font-weight: 500;
}

.company-logo {
  width: 18px;
  height: 18px;
  border-radius: 4px;
}

.job-desc {
  font-size: 14px;
  color: #4b5563;
  margin: 0 0 20px;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.job-salary {
  color: #9333ea;
  font-size: 17px;
  font-weight: 800;
}

.job-card-footer {
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid #e5e7eb;
  padding-top: 16px;
  margin-top: auto;
}

.detail-link {
  color: #6b7280;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  transition: color 0.3s;
}
.job-card:hover .detail-link {
  color: #3b82f6;
}

/* Report Card Styles */
.report-card {
  background: linear-gradient(145deg, #ffffff 0%, #f9fafb 100%);
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  min-height: 340px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02), inset 0 1px 0 rgba(255, 255, 255, 1);
  transition: all 0.4s ease;
}

.report-card:hover {
  box-shadow: 0 20px 40px -10px rgba(59, 130, 246, 0.1), inset 0 1px 0 rgba(255, 255, 255, 1);
  border-color: rgba(59, 130, 246, 0.3);
}

.report-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 32px 24px;
}

.report-score-wrap {
  text-align: center;
  margin-bottom: 24px;
}

.score-circle {
  width: 120px;
  height: 120px;
  margin: 0 auto 20px;
  border-radius: 50%;
  background: conic-gradient(from 180deg at 50% 50%, #3b82f6 -7.5deg, #a855f7 165deg, #3b82f6 352.5deg);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #111827;
  box-shadow: 0 8px 16px rgba(147, 51, 234, 0.15);
  position: relative;
}

.score-circle::after {
  content: '';
  position: absolute;
  inset: 5px;
  background: #ffffff;
  border-radius: 50%;
  z-index: 1;
}

.score-num {
  font-size: 38px;
  font-weight: 800;
  color: #111827;
  z-index: 2;
  line-height: 1;
  letter-spacing: -1px;
}

.score-unit {
  font-size: 14px;
  color: #9333ea;
  z-index: 2;
  margin-top: 4px;
  font-weight: 600;
}

.score-label {
  font-size: 15px;
  font-weight: 700;
  color: #4b5563;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.report-summary {
  font-size: 14px;
  color: #4b5563;
  margin: 0 0 24px;
  line-height: 1.6;
  flex: 1;
  background: #f9fafb;
  padding: 16px 20px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  position: relative;
}

.report-summary::before {
  content: '“';
  font-size: 44px;
  color: #e5e7eb;
  position: absolute;
  top: -12px;
  left: 12px;
  font-family: serif;
  line-height: 1;
}

.report-action {
  margin-top: auto;
}

.full-btn {
  width: 100%;
  height: 44px;
  font-weight: 600;
  font-size: 15px;
  background: linear-gradient(180deg, #1f2937, #000000);
  border: 1px solid #000000;
  color: #ffffff;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.1);
}

.full-btn:hover {
  background: #333333;
  transform: translateY(-2px);
  box-shadow: 0 8px 15px rgba(0,0,0,0.15);
}

/* Footer Styles */
.home-footer {
  position: relative;
  z-index: 10;
  margin-top: 80px;
  padding: 50px 0;
  background: #ffffff;
  text-align: center;
  border-top: 1px solid #e5e7eb;
}

.home-footer-inner {
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 20px;
  font-weight: 800;
  color: #111827;
  letter-spacing: -0.5px;
}
.logo-icon {
  color: #111827;
  font-size: 22px;
}

.home-footer-desc {
  margin: 0;
  color: #6b7280;
  font-size: 14px;
  font-weight: 500;
}

.footer-copyright {
  font-size: 13px;
  color: #9ca3af;
  margin-top: 8px;
}

/* Animations */
.fade-in-up {
  animation: fadeInUp 0.8s cubic-bezier(0.25, 0.8, 0.25, 1) forwards;
  opacity: 0;
  transform: translateY(20px);
}

.delay-1 {
  animation-delay: 0.15s;
}

.delay-2 {
  animation-delay: 0.3s;
}
@keyframes fadeInUp {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
