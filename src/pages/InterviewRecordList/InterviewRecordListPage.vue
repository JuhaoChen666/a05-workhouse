<template>
  <div class="record-list-page">
    <h2 class="page-title">全部面试记录</h2>
    <el-card shadow="hover">
      <el-table v-loading="loading" :data="list" stripe>
        <el-table-column prop="positionName" label="岗位" width="140" />
        <el-table-column prop="startedAt" label="开始时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.startedAt) }}</template>
        </el-table-column>
        <el-table-column prop="endedAt" label="结束时间" width="180">
          <template #default="{ row }">{{ row.endedAt ? formatDateTime(row.endedAt) : '--' }}</template>
        </el-table-column>
        <el-table-column prop="totalScore" label="得分" width="80">
          <template #default="{ row }">{{ row.totalScore ?? '--' }}</template>
        </el-table-column>
        <el-table-column label="操作" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="goReport(row.id)">查看报告</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        @current-change="fetchList"
        @size-change="fetchList"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { getInterviewRecordListApi, type InterviewRecordItem } from '@/api/interview';

const router = useRouter();
const loading = ref(false);
const list = ref<InterviewRecordItem[]>([]);
const pagination = reactive({ page: 1, pageSize: 10, total: 0 });

function formatDateTime(iso: string) {
  if (!iso) return '--';
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function goReport(id: number) {
  router.push({ name: 'ReportDetail', params: { id: String(id) } });
}

async function fetchList() {
  loading.value = true;
  try {
    const res = await getInterviewRecordListApi({ page: pagination.page, pageSize: pagination.pageSize });
    list.value = res.list ?? [];
    pagination.total = res.total ?? 0;
  } finally {
    loading.value = false;
  }
}

onMounted(() => fetchList());
</script>

<style scoped>
.record-list-page { max-width: 900px; }
.page-title { margin-top: 0; margin-bottom: 16px; }
.pagination { margin-top: 16px; justify-content: flex-end; }
</style>
