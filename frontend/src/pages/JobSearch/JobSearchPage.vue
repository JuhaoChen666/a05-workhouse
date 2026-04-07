<template>
  <div class="job-search-page">
    <!-- 搜索与高级筛选区域 -->
    <el-card class="search-bar-card" shadow="never">
      <div class="search-bar">
        <el-input
          v-model="keyword"
          placeholder="搜索岗位名称 / 公司 / 关键词"
          clearable
          class="keyword-input"
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select
          v-model="jobType"
          placeholder="岗位类型"
          clearable
          class="type-select"
        >
          <el-option
            v-for="item in jobTypeOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
        <el-button type="primary" @click="handleSearch">搜索</el-button>
      </div>
    </el-card>

    <!-- 搜索结果列表 -->
    <el-card class="result-card" shadow="never">
      <template #header>
        <div class="result-header">
          <span>搜索结果</span>
          <span class="result-count">
            共 {{ total }} 条记录
          </span>
        </div>
      </template>

      <el-empty
        v-if="!loading && jobs.length === 0"
        description="暂无匹配的岗位"
        :image-size="80"
      />

      <el-skeleton :loading="loading" animated>
        <template #template>
          <el-skeleton-item variant="p" style="margin-bottom: 12px" />
          <el-skeleton-item variant="p" style="margin-bottom: 12px" />
          <el-skeleton-item variant="p" />
        </template>
        <template #default>
          <div class="result-body-scroll">
            <el-row :gutter="16">
              <el-col v-for="job in jobs" :key="job.id" :span="12" class="job-col">
                <el-card
                  shadow="hover"
                  class="job-card"
                  @click="goJobDetail(job.id)"
                >
                  <div class="job-card-header">
                    <div>
                      <div class="job-name" v-html="highlightText(job.name)" />
                      <div class="company-name">
                        <img
                          v-if="job.companyLogo"
                          :src="`/img/${job.companyLogo}.ico`"
                          class="company-logo"
                          alt="company logo"
                        />
                        <span v-html="highlightText(job.companyName)" />
                      </div>
                    </div>
                    <el-tag v-if="job.type" size="small" type="info">
                      {{ formatJobType(job.type) }}
                    </el-tag>
                  </div>
                  <p class="job-desc" v-html="highlightText((job.jobContent || '').slice(0, 80) + '...')" />
                  <div class="job-footer">
                    <span class="job-salary">
                      {{ formatSalaryRange(job.salaryMin, job.salaryMax) }}
                    </span>
                    <el-button type="primary" link @click.stop="goJobDetail(job.id)">
                      查看详情
                    </el-button>
                  </div>
                </el-card>
              </el-col>
            </el-row>
          </div>

          <div class="pager-wrap" v-if="total > pageSize">
            <el-pagination
              v-model:current-page="page"
              :page-size="pageSize"
              layout="total, sizes, prev, pager, next"
              :total="total"
              :page-sizes="[8, 12, 20]"
              @current-change="handlePageChange"
              @size-change="handlePageSizeChange"
            />
          </div>
        </template>
      </el-skeleton>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Search } from '@element-plus/icons-vue';
import {
  searchJobsApi,
  formatSalaryRange,
  type HotJobItem,
  type SearchJobsParams,
} from '@/api/jobs';

// 路由对象
const route = useRoute();
const router = useRouter();

// 搜索条件
const keyword = ref<string>('');
const jobType = ref<string | undefined>();
const page = ref<number>(1);
const pageSize = ref<number>(8);

// 搜索结果
const jobs = ref<HotJobItem[]>([]);
const total = ref<number>(0);
const loading = ref<boolean>(false);

// 最近一次已执行搜索使用的关键字（用于高亮，不随输入框实时变化）
const lastSearchKeyword = ref<string>('');
// 当前高亮关键字（仅在有 lastSearchKeyword 时生效）
const highlightKeyword = computed(() => (lastSearchKeyword.value || '').trim());

// 岗位类型选项（需与后端约定保持一致）
const jobTypeOptions = [
  { label: '全部类型', value: '' },
  { label: '后端开发', value: 'backend' },
  { label: '前端开发', value: 'frontend' },
  { label: '算法工程师', value: 'algo' },
  { label: '全栈开发', value: 'fullstack' },
  { label: '其它', value: 'other' },
];

// 将岗位类型编码映射为中文文案
function formatJobType(type: string) {
  const mapping: Record<string, string> = {
    backend: '后端开发',
    frontend: '前端开发',
    algo: '算法工程师',
    fullstack: '全栈开发',
    other: '其它',
  };
  return mapping[type] || type;
}

// 从路由 query 初始化搜索条件
function initFromQuery() {
  const q = route.query || {};
  keyword.value = (q.keyword as string) || '';
  jobType.value = (q.type as string) || undefined;
  page.value = q.page ? Number(q.page) || 1 : 1;
  // 初始场景下，高亮跟随路由中的 keyword，而不是输入框的实时内容
  lastSearchKeyword.value = (keyword.value || '').trim();
}

// 执行搜索请求
async function fetchJobs() {
  const params: SearchJobsParams = {
    keyword: keyword.value || undefined,
    type: jobType.value || undefined,
    page: page.value,
    pageSize: pageSize.value,
  };
  loading.value = true;
  try {
    const res = await searchJobsApi(params);
    jobs.value = res?.list ?? [];
    total.value = res?.total ?? 0;
  } finally {
    loading.value = false;
  }
}

// 点击搜索按钮或回车
function handleSearch() {
  page.value = 1;
  router.replace({
    name: 'JobSearch',
    query: {
      keyword: keyword.value || undefined,
      type: jobType.value || undefined,
      page: page.value,
    },
  });
  // 仅在真正触发搜索时更新高亮关键字
  lastSearchKeyword.value = (keyword.value || '').trim();
  fetchJobs();
}

// 分页切换
function handlePageChange(p: number) {
  page.value = p;
  router.replace({
    name: 'JobSearch',
    query: {
      keyword: keyword.value || undefined,
      type: jobType.value || undefined,
      page: page.value,
    },
  });
  fetchJobs();
}

// 修改每页条数
function handlePageSizeChange(size: number) {
  pageSize.value = size;
  page.value = 1;
  router.replace({
    name: 'JobSearch',
    query: {
      keyword: keyword.value || undefined,
      type: jobType.value || undefined,
      page: page.value,
    },
  });
  fetchJobs();
}

// 跳转岗位详情
function goJobDetail(id: number) {
  router.push({ name: 'JobDetail', params: { id: String(id) } });
}

// 高亮文案中的搜索关键字；后端未传 keyword（或为空）时不高亮
function highlightText(text?: string | null) {
  const value = text || '';
  const kw = highlightKeyword.value;
  if (!kw) return value;

  try {
    const escaped = kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const reg = new RegExp(escaped, 'gi');
    return value.replace(reg, (match) => `<span class="kw-highlight">${match}</span>`);
  } catch {
    return value;
  }
}

onMounted(() => {
  initFromQuery();
  fetchJobs();
});

// 监听路由变化，支持从外部更新查询参数
watch(
  () => route.query,
  () => {
    initFromQuery();
    fetchJobs();
  }
);
</script>

<style scoped>
.job-search-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.search-bar-card {
  padding-bottom: 0;
}
.search-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}
.keyword-input {
  flex: 1;
}
.type-select {
  width: 160px;
}
.result-card {
  min-height: 260px;
  max-height: calc(100vh - 220px);
  display: flex;
  flex-direction: column;
}
.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
}
.result-count {
  color: #909399;
}
.result-body-scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  /* 默认隐藏滚动条（Firefox） */
  scrollbar-width: none;
}

/* 鼠标悬停时，显示较细的滚动条（Firefox） */
.result-body-scroll:hover {
  scrollbar-width: thin;
}

/* WebKit 浏览器下的滚动条样式控制 */
.result-body-scroll::-webkit-scrollbar {
  width: 0;
  height: 0;
}

.result-body-scroll:hover::-webkit-scrollbar {
  width: 4px;
}

.result-body-scroll::-webkit-scrollbar-track {
  background-color: transparent;
}

.result-body-scroll::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.12);
  border-radius: 2px;
}
:deep(.kw-highlight) {
  color: #e6a23c;
  border-radius: 2px;
  padding: 0 1px;
}
.job-col {
  margin-bottom: 16px;
}
.job-card {
  cursor: pointer;
}
.job-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}
.job-name {
  font-weight: 600;
  margin-bottom: 4px;
}
.company-name {
  font-size: 12px;
  color: #909399;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.company-logo {
  width: 16px;
  height: 16px;
}
.job-desc {
  font-size: 13px;
  color: #606266;
  margin: 0 0 8px;
  line-height: 1.4;
}
.job-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.job-salary {
  color: #e6a23c;
  font-weight: 500;
}
.pager-wrap {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
}
</style>

