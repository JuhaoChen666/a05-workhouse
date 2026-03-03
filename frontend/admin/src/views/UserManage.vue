<template>
  <div class="page">
    <el-card>
      <template #header>
        <span>用户列表</span>
      </template>
      <el-table v-loading="loading" :data="list" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="email" label="邮箱" min-width="160" />
        <el-table-column prop="roleName" label="角色" width="100" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default>
            <span class="muted">仅查看</span>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
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
import { ref, onMounted } from 'vue';
import { getUserListApi } from '@/api/admin';
import type { UserItem } from '@/api/admin';

const loading = ref(false);
const list = ref<UserItem[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(10);

async function fetchList() {
  loading.value = true;
  try {
    const res = await getUserListApi({ page: page.value, pageSize: pageSize.value });
    list.value = res.list;
    total.value = res.total;
  } finally {
    loading.value = false;
  }
}

onMounted(fetchList);
</script>

<style scoped>
.page {
  min-height: 400px;
}

.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}

.muted {
  color: #909399;
  font-size: 12px;
}
</style>
