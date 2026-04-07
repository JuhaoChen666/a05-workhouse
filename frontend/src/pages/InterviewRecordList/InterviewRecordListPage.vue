<template>
  <div class="record-list-page theme-page-shell">
    <div class="theme-section-header fade-in-up">
      <h2 class="theme-section-title">全部面试记录 <span>Records</span></h2>
      <div class="theme-section-decoration"></div>
    </div>
    <el-card shadow="hover" class="theme-card fade-in-up delay-1">
      <el-table v-loading="loading" :data="list" stripe>
        <el-table-column prop="session_id" label="会话ID" min-width="260" show-overflow-tooltip />
        <el-table-column label="岗位" min-width="160">
          <template #default="{ row }">{{ row.position_name || row.position || '--' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="开始时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="{ row }">{{ row.updated_at ? formatDateTime(row.updated_at) : '--' }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : 'warning'" size="small">
              {{ row.status === 'completed' ? '已完成' : '进行中' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="onRecordClick(row)">
              {{ row.status === 'completed' ? '查看报告' : '继续面试' }}
            </el-button>
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
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  getUserInterviewSessionsPageApi,
  endInterviewSessionApi,
  type UserInterviewSessionItem,
} from '@/api/interviewAi';
import { useUserStore } from '@/store/user';

const router = useRouter();
const userStore = useUserStore();
const loading = ref(false);
const list = ref<UserInterviewSessionItem[]>([]);
const pagination = reactive({ page: 1, pageSize: 10, total: 0 });

function formatDateTime(iso: string) {
  if (!iso) return '--';
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

async function onRecordClick(row: UserInterviewSessionItem) {
  const sid = String(row.session_id || '').trim();
  if (!sid) return;
  const job = (row.position_name || row.position || '').trim();
  if (row.status === 'completed') {
    router.push({
      name: 'InterviewEvaluation',
      params: { sessionId: sid },
      query: { jobName: job || undefined },
    });
    return;
  }
  try {
    await ElMessageBox.confirm(
      '该面试尚未完成。你可以继续当前会话，或直接结束本次面试。',
      '面试未完成',
      {
        confirmButtonText: '继续面试',
        cancelButtonText: '结束面试',
        distinguishCancelAndClose: true,
        type: 'warning',
      }
    );
    router.push({
      name: 'InterviewSession',
      params: { id: sid },
      query: {
        sessionId: sid,
        jobName: job || undefined,
        fromRecord: '1',
      },
    });
  } catch (e) {
    if (e !== 'cancel') return;
    try {
      await endInterviewSessionApi(sid);
      ElMessage.success('已结束本次面试');
      await fetchList();
    } catch (err: unknown) {
      ElMessage.error((err as Error).message || '结束面试失败');
    }
  }
}

async function fetchList() {
  const userId = userStore.userInfo?.id;
  if (!userId) return;
  loading.value = true;
  try {
    const res = await getUserInterviewSessionsPageApi(userId, {
      page: pagination.page,
      pageSize: pagination.pageSize,
    });
    list.value = res.list ?? [];
    pagination.total = res.total ?? 0;
  } finally {
    loading.value = false;
  }
}

onMounted(() => fetchList());
</script>

<style scoped>
.record-list-page { max-width: 1200px; }
.pagination { margin-top: 16px; justify-content: flex-end; }
</style>
