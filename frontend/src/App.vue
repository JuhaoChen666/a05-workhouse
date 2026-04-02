<template>
  <router-view v-slot="{ Component }">
    <transition name="fade-slide" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<script setup lang="ts">
// 根组件保持简单，直接展示路由页面
</script>

<style>
html {
  /* 预留滚动条空间，彻底解决页面切换时由于滚动条消失产生的水平抖动 */
  scrollbar-gutter: stable;
  /* 如果部分老式浏览器不支持 scrollbar-gutter，可以开启下面这行强制显示滚动条轨道： */
  /* overflow-y: scroll; */
}

html,
body,
#app {
  margin: 0;
  padding: 0;
  height: 100%;
}

/* Global Page Transition Animations */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(15px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-15px);
}
</style>