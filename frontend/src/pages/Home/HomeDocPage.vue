<template>
  <div class="help-doc-page fade-in-up delay-1">
    <header class="help-doc-head theme-card">
      <h1 class="help-doc-title">使用帮助</h1>
      <p class="help-doc-lead">
        本页为面试训练平台的操作说明，按功能模块划分。侧栏可快速进入对应功能；文中「前往」链接仅在登录后可用。
      </p>
      <nav class="help-toc" aria-label="文档目录">
        <button
          v-for="item in tocItems"
          :key="item.id"
          type="button"
          class="help-toc-btn"
          @click="scrollToSection(item.id)"
        >
          {{ item.label }}
        </button>
      </nav>
    </header>

    <div class="help-sections">
      <article id="section-nav" class="help-block theme-card">
        <h2>界面与导航</h2>
        <ul class="help-list">
          <li>登录后主界面为「首页工作台」：含模拟面试入口、快速入口卡片、情报与热门岗位等模块。</li>
          <li>左侧竖栏（悬停或移动端展开）可切换：<strong>首页</strong>、<strong>面试</strong>（面试设置向导）、<strong>AI押题</strong>、<strong>简历管理</strong>、<strong>帮助文档</strong>。</li>
          <li>右上角头像下拉可进入<strong>个人中心</strong>或退出登录。</li>
        </ul>
        <div class="help-actions">
          <RouterLink class="help-link" :to="{ name: 'Home' }">前往首页</RouterLink>
        </div>
      </article>

      <article id="section-interview" class="help-block theme-card">
        <h2>模拟面试（AI 面试 / 虚拟人面试）</h2>
        <p class="help-p">
          从侧栏「面试」或首页「立即开始面试」进入。向导共三步：选择模式 → 选择岗位 → 面试配置，完成后进入正式面试页。
        </p>
        <h3 class="help-h3">第一步：选择面试模式</h3>
        <ol class="help-ol">
          <li><strong>AI面试</strong>：文本/语音交互，侧重答题与追问，适合日常刷题与表达训练。</li>
          <li><strong>虚拟人面试</strong>：虚拟面试官形象与口播，氛围更接近真实面试。</li>
          <li>首页「快速入口」中带参数跳转时，会直接进入对应模式并进入下一步。</li>
        </ol>
        <el-alert type="info" :closable="false" show-icon class="help-alert">
          虚拟人模式通常需要在 <strong>HTTPS</strong> 或安全环境下使用麦克风；部署时需配置虚拟人 SDK 脚本地址等环境变量，否则可能无法初始化。
        </el-alert>
        <h3 class="help-h3">第二步：选择岗位</h3>
        <ol class="help-ol">
          <li>在列表或搜索结果中选择目标岗位（可结合职责描述判断匹配度）。</li>
          <li>选中后进入下一步；如需更换岗位，可使用向导中的「上一步」返回。</li>
        </ol>
        <h3 class="help-h3">第三步：面试配置</h3>
        <ol class="help-ol">
          <li>选择面试官形象等选项（具体项以页面为准）。</li>
          <li>进行麦克风检测时，请允许浏览器麦克风权限；若提示不可用，请检查是否为安全上下文（HTTPS）、设备与浏览器权限设置。</li>
          <li>确认无误后开始面试，系统将创建会话并进入答题界面。</li>
        </ol>
        <h3 class="help-h3">面试进行中</h3>
        <ul class="help-list">
          <li>按页面提示作答；虚拟人模式需关注语音采集与播放状态。</li>
          <li>结束或离开前请使用页面上的结束/离开操作，必要时在二次确认对话框中确认，以免丢失进度。</li>
        </ul>
        <h3 class="help-h3">面试结束后</h3>
        <p class="help-p">根据流程跳转可查看评估或报告（以实际页面提示为准）。</p>
        <div class="help-actions">
          <RouterLink class="help-link" :to="{ name: 'HomeInterviewType' }">前往面试设置</RouterLink>
        </div>
      </article>

      <article id="section-question" class="help-block theme-card">
        <h2>AI 押题</h2>
        <p class="help-p">用于按岗位生成模拟面试题清单，支持流式生成与导出。</p>
        <ol class="help-ol">
          <li>在向导<strong>第一步</strong>选择或检索岗位，选中目标岗位。</li>
          <li>进入<strong>生成题目</strong>步骤后，系统会逐题生成；左侧为当前题目内容，右侧为题号目录（小方格布局）。</li>
          <li>点击右侧题号可切换查看已生成的题目；生成过程中会自动跟随最新一题。</li>
          <li>全部题目生成完成后，会出现<strong>导出 PDF</strong>按钮，可将当前题单导出为 PDF（含排版样式）。未完成前不会显示导出。</li>
          <li>生成过程中请保持页面打开，网络异常时可稍后从本模块重新进入重试。</li>
        </ol>
        <div class="help-actions">
          <RouterLink class="help-link" :to="{ name: 'HomeQuestion' }">前往 AI 押题</RouterLink>
        </div>
      </article>

      <article id="section-resume" class="help-block theme-card">
        <h2>简历管理与简历优化</h2>
        <h3 class="help-h3">简历管理</h3>
        <ol class="help-ol">
          <li>在「简历管理」页可<strong>上传简历</strong>：目前仅支持 <strong>PDF</strong> 格式。</li>
          <li>上传前可先预览确认文件内容，再确认上传。</li>
          <li>列表中可查看摘要、打开预览、删除不需要的版本；简历将用于后续面试等能力的数据来源。</li>
        </ol>
        <h3 class="help-h3">简历优化</h3>
        <ol class="help-ol">
          <li>在简历管理页可进入「简历优化」流程，按引导上传或选择材料。</li>
          <li>优化过程中请关注进度提示；完成后可查看优化结果（具体展示以页面为准）。</li>
          <li>首页快速入口「简历优化」可直达优化相关页面。</li>
        </ol>
        <div class="help-actions">
          <RouterLink class="help-link" :to="{ name: 'HomeResume' }">前往简历管理</RouterLink>
          <RouterLink class="help-link" :to="{ name: 'HomeResumeGeneration' }">前往 LaTeX 简历生成</RouterLink>
        </div>
      </article>

      <article id="section-job" class="help-block theme-card">
        <h2>岗位检索</h2>
        <p class="help-p">
          系统提供岗位检索与详情能力（路由：<code>/home/job</code>）。在检索框输入关键词，浏览结果卡片；点击可查看岗位详情、职责与要求等信息，便于投递前整理或与模拟面试选题结合。
        </p>
        <div class="help-actions">
          <RouterLink class="help-link" :to="{ name: 'HomeJob' }">前往岗位检索</RouterLink>
        </div>
      </article>

      <article id="section-record" class="help-block theme-card">
        <h2>面试记录与报告</h2>
        <ul class="help-list">
          <li>在<strong>个人中心</strong>的「最近面试记录」区域，点击<strong>查看全部面试记录</strong>可打开历史会话列表。</li>
          <li>在列表或后续入口中可打开单场<strong>面试报告/详情</strong>，回顾表现与反馈（以页面实际字段为准）。</li>
        </ul>
        <div class="help-actions">
          <RouterLink class="help-link" :to="{ name: 'Profile' }">前往个人中心</RouterLink>
        </div>
      </article>

      <article id="section-profile" class="help-block theme-card">
        <h2>个人中心与账户设置</h2>
        <ol class="help-ol">
          <li><strong>个人中心</strong>展示用户名、邮箱等资料；「角色」等管理标识仅对管理员账号显示。</li>
          <li>使用「编辑资料」或账户相关入口可修改密码、头像等信息；页面顶部提供返回个人中心的快捷操作。</li>
          <li>管理员账号在个人中心还可进入<strong>后台管理系统</strong>。</li>
        </ol>
        <div class="help-actions">
          <RouterLink class="help-link" :to="{ name: 'Profile' }">前往个人中心</RouterLink>
          <RouterLink class="help-link" :to="{ name: 'ProfileEdit' }">前往编辑资料</RouterLink>
        </div>
      </article>

      <article id="section-admin" class="help-block theme-card">
        <h2>后台管理系统（管理员）</h2>
        <p class="help-p">仅管理员可访问 <code>/admin</code> 下各模块，普通用户会被拦截并提示。</p>
        <ul class="help-list">
          <li><strong>用户管理</strong>：维护账号与角色等。</li>
          <li><strong>简历管理 / 会话管理</strong>：查看或运维侧数据（以实际菜单为准）。</li>
          <li><strong>岗位管理</strong>：维护岗位信息；接口带 <code>/admin</code> 前缀时需与网关、Nginx 反代配置一致。</li>
          <li><strong>题库管理、学习资源</strong>：内容与资源维护入口。</li>
          <li>退出后台后应回到登录页；若遇白屏，可尝试刷新或清除缓存后重新登录。</li>
        </ul>
        <div v-if="userStore.isAdmin" class="help-actions">
          <RouterLink class="help-link" :to="{ name: 'AdminUsers' }">前往后台管理</RouterLink>
        </div>
      </article>

      <article id="section-trouble" class="help-block theme-card">
        <h2>常见问题提示</h2>
        <ul class="help-list">
          <li><strong>麦克风不可用</strong>：确认站点为 HTTPS（或 localhost）、浏览器已授权麦克风，且未被其他应用独占。</li>
          <li><strong>虚拟人无法加载</strong>：检查环境变量中 SDK 脚本地址是否已配置且网络可达。</li>
          <li><strong>接口 404 / 跨域</strong>：确认前端请求的 API 基地址与 Nginx 中 <code>/api/</code>、<code>/admin/</code> 反代是否一致。</li>
        </ul>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router';
import { useUserStore } from '@/store/user';

const userStore = useUserStore();

const tocItems = [
  { id: 'section-nav', label: '界面与导航' },
  { id: 'section-interview', label: '模拟面试' },
  { id: 'section-question', label: 'AI押题' },
  { id: 'section-resume', label: '简历' },
  { id: 'section-job', label: '岗位检索' },
  { id: 'section-record', label: '记录与报告' },
  { id: 'section-profile', label: '个人中心' },
  { id: 'section-admin', label: '后台管理' },
  { id: 'section-trouble', label: '常见问题' },
];

function scrollToSection(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
</script>

<style scoped>
.help-doc-page {
  max-width: 920px;
  margin: 0 auto;
  padding-bottom: 32px;
}
.help-doc-head {
  padding: 22px 24px;
  margin-bottom: 16px;
}
.help-doc-title {
  margin: 0 0 8px;
  font-size: 1.5rem;
  font-weight: 800;
  color: #111827;
  letter-spacing: -0.02em;
}
.help-doc-lead {
  margin: 0 0 16px;
  font-size: 14px;
  line-height: 1.65;
  color: #64748b;
}
.help-toc {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.help-toc-btn {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
.help-toc-btn:hover {
  background: #eef2ff;
  border-color: #c4b5fd;
  color: #4338ca;
}
.help-sections {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.help-block {
  padding: 20px 22px;
  scroll-margin-top: 88px;
}
.help-block h2 {
  margin: 0 0 12px;
  font-size: 1.15rem;
  font-weight: 800;
  color: #1e293b;
}
.help-h3 {
  margin: 16px 0 8px;
  font-size: 14px;
  font-weight: 700;
  color: #334155;
}
.help-p {
  margin: 0 0 10px;
  font-size: 14px;
  line-height: 1.7;
  color: #475569;
}
.help-list,
.help-ol {
  margin: 0 0 10px;
  padding-left: 1.25rem;
  font-size: 14px;
  line-height: 1.75;
  color: #475569;
}
.help-list li + li,
.help-ol li + li {
  margin-top: 6px;
}
.help-alert {
  margin-top: 10px;
}
.help-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
}
.help-link {
  display: inline-flex;
  align-items: center;
  font-size: 13px;
  font-weight: 600;
  color: #4f46e5;
  text-decoration: none;
  padding: 6px 12px;
  border-radius: 8px;
  background: #eef2ff;
  transition: background 0.15s ease, color 0.15s ease;
}
.help-link:hover {
  background: #e0e7ff;
  color: #3730a3;
}
.help-block code {
  font-size: 12px;
  padding: 1px 6px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #0f172a;
}
@media (max-width: 768px) {
  .help-doc-head {
    padding: 16px;
  }
  .help-block {
    padding: 16px;
    scroll-margin-top: 72px;
  }
}
</style>
