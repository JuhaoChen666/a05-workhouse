<template>
  <!-- 用户列表页：仅管理员可见，用于查看所有用户 -->
  <div class="page">
    <el-card>
      <template #header>
        <span>用户列表</span>
      </template>
      <!-- 用户表格 -->
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
      <!-- 分页 -->
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
import { getUserListApi, type AdminUserItem } from '@/api/admin';

// 表格加载状态
const loading = ref(false);
// 用户数据列表
const list = ref<AdminUserItem[]>([]);
// 总条数与分页信息
const total = ref(0);
const page = ref(1);
const pageSize = ref(10);

/**
 * 从后端拉取用户列表数据
 */
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

// 页面挂载时加载一次数据
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

