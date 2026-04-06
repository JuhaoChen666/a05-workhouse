<template>
  <!-- 岗位详情页：展示 admin /positions/:id 返回的完整数据结构 -->
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>岗位详情（ID：{{ id }}）</span>
          <el-button @click="goBack">返回列表</el-button>
        </div>
      </template>

      <el-skeleton v-if="loading" rows="6" animated />

      <div v-else>
        <!-- 结构化展示常用字段 -->
        <el-descriptions title="基本信息" :column="2" border>
          <el-descriptions-item label="岗位名称">
            {{ detail?.name }}
          </el-descriptions-item>
          <el-descriptions-item label="城市">
            {{ detail?.city }}
          </el-descriptions-item>
          <el-descriptions-item label="排序值">
            {{ detail?.sortOrder }}
          </el-descriptions-item>
          <el-descriptions-item label="薪资范围">
            <span v-if="detail">
              {{ detail.salaryMin }} - {{ detail.salaryMax }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="工作经验">
            {{ detail?.workExperience }}
          </el-descriptions-item>
          <el-descriptions-item label="学历要求">
            {{ detail?.education }}
          </el-descriptions-item>
          <el-descriptions-item label="标签" :span="2">
            <el-tag
              v-for="t in detail?.tags || []"
              :key="t"
              size="small"
              style="margin-right: 8px"
            >
              {{ t }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <el-descriptions title="职责描述" :column="1" border style="margin-top: 20px">
          <el-descriptions-item>
            <div class="pre-text">
              {{ detail?.responsibilities }}
            </div>
          </el-descriptions-item>
        </el-descriptions>

        <el-descriptions title="任职要求" :column="1" border style="margin-top: 20px">
          <el-descriptions-item>
            <div class="pre-text">
              {{ detail?.requirements }}
            </div>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 原始 JSON 数据，方便对照接口结构 -->
        <el-card class="raw-card" shadow="never">
          <template #header>
            <span>原始数据（/admin/positions/:id 响应）</span>
          </template>
          <pre class="json">{{ formattedJson }}</pre>
        </el-card>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { getPositionDetailApi } from '@/api/admin';

// 当前路由与路由实例
const route = useRoute();
const router = useRouter();

// 岗位 ID（从路由参数获取）
const id = Number(route.params.id);

// 加载状态与详情数据
const loading = ref(false);
const detail = ref<Record<string, unknown> | null>(null);

/** 返回列表页 */
function goBack() {
  router.push({ name: 'AdminPositions' });
}

/** 加载岗位详情数据 */
async function fetchDetail() {
  if (!id) return;
  loading.value = true;
  try {
    const res = await getPositionDetailApi(id);
    detail.value = res as Record<string, unknown>;
  } finally {
    loading.value = false;
  }
}

// 美化 JSON 文本，方便查看全部字段
const formattedJson = computed(() =>
  detail.value ? JSON.stringify(detail.value, null, 2) : ''
);

// 页面加载时拉一次详情
onMounted(fetchDetail);
</script>

<style scoped>
.page {
  min-height: 400px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pre-text {
  white-space: pre-wrap;
  line-height: 1.6;
}

.raw-card {
  margin-top: 24px;
}

.json {
  margin: 0;
  font-family: Menlo, Monaco, Consolas, 'Courier New', monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>

