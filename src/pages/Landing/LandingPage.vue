<template>
  <div class="landing">
    <!-- Textured Background -->
    <div class="bg-pattern"></div>
    <div class="bg-layer"></div>

    <!-- Header -->
    <header class="landing-header">
      <div class="header-left">
        <div class="logo">
          <el-icon class="logo-icon"><Platform /></el-icon>
          <span class="logo-text">AI 面试官</span>
        </div>
        <div class="picture-logo">
          <img src="@/assets/logo1.png" alt="Logo" style="width: 50px; height: 50px;" />
        </div>
        <!-- Textured Nav Links -->
        <nav class="nav-links-container">
          <div class="nav-links">
            <a href="#home" class="active">首页</a>
            <a href="#features">核心功能</a>
          </div>
        </nav>
      </div>

      <div class="actions">
        <el-button class="login-btn" text @click="goLogin">登录</el-button>
        <el-button class="register-btn" @click="goRegister">免费注册</el-button>
      </div>
    </header>

    <!-- Main Content -->
    <main class="landing-main">
      <!-- Hero Section -->
      <section id="home" class="hero">
        <div class="hero-content">
          <h1 class="title">
            掌控面试节奏<br />
            <span class="highlight">斩获理想 Offer</span>
          </h1>
          <p class="subtitle">
            沉浸式还原真实技术面试场景，结合大语言模型的深度解析，为你提供全方位、多维度的面试表现评估与专家级改进建议。
          </p>
          <div class="hero-actions">
            <el-button size="large" class="start-btn" @click="goLogin">
              立即开启模拟面试
            </el-button>
          </div>
          <div class="stats">
            <div class="stat-item">
              <span class="stat-num">10,000+</span>
              <span class="stat-desc">已帮助候选人</span>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-num">500+</span>
              <span class="stat-desc">覆盖岗位题库</span>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-num">98%</span>
              <span class="stat-desc">好评率</span>
            </div>
          </div>
        </div>
        
        <div class="hero-visual">
          <div class="mock-window">
            <div class="window-header">
              <span class="dot red"></span>
              <span class="dot yellow"></span>
              <span class="dot green"></span>
            </div>
            <div class="window-body">
              <div class="ai-chat">
                <div class="chat-msg ai">请简述一下 Vue3 中 Proxy 相比 Object.defineProperty 的优势有哪些？</div>
                <div class="chat-msg user style-typing">思考中...</div>
              </div>
              <div class="analysis-card">
                <div class="card-title">AI 实时分析</div>
                <el-progress :percentage="85" color="#9333ea" :stroke-width="6" />
                <div class="card-desc">技术栈匹配度优秀，表达流畅。</div>
              </div>
            </div>
          </div>
          <!-- Reduced floating cards to match cleaner aesthetic -->
          <div class="float-card card-1">
            <el-icon class="icon"><DocumentChecked /></el-icon>
            <span>深度简历解析</span>
          </div>
        </div>
      </section>

      <!-- Features Section -->
      <section id="features" class="features">
        <h2 class="section-title">核心功能及特性</h2>
        <div class="feature-grid">
          <div class="feature-card" v-for="(feature, index) in features" :key="index">
            <div class="icon-wrapper">
              <el-icon><component :is="feature.icon" /></el-icon>
            </div>
            <h3>{{ feature.title }}</h3>
            <p>{{ feature.desc }}</p>
          </div>
        </div>
      </section>

      <!-- Logos Section -->
      <section class="trust-section">
        <p class="trust-title">受到众多优秀开发者与求职者的信赖</p>
        <div class="trust-logos">
          <span class="trust-brand">SAMSUNG</span>
          <span class="trust-brand">ORACLE</span>
          <span class="trust-brand">amazon</span>
          <span class="trust-brand">LG</span>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import {
  Platform, DocumentChecked, DataLine, Microphone, Aim, Medal, DataAnalysis, ChatDotRound
} from '@element-plus/icons-vue';

const router = useRouter();

const goLogin = () => {
  router.push({ name: 'Login' });
};

const goRegister = () => {
  router.push({ name: 'Register' });
};

const features = [
  {
    icon: Microphone,
    title: '智能语音交互',
    desc: '拟真语音对话体验，AI面试官实时提问、追问，还原高压真实面试场景。'
  },
  {
    icon: DocumentChecked,
    title: '简历定向分析',
    desc: '一键导入简历，提炼核心项目经历与技术栈，生成专属定制化面试题库。'
  },
  {
    icon: DataAnalysis,
    title: '全方位能力评估',
    desc: '从技术深度、沟通表达、逻辑思维等多维度输出结构化面试报告。'
  },
  {
    icon: ChatDotRound,
    title: '逐题反馈与解答',
    desc: '针对每道题目给出标准参考答案、评分依据及个性化改进建议。'
  },
  {
    icon: Aim,
    title: '海量场景自选',
    desc: '支持前端、后端、算法、大厂面、HR面等数十种细分行业与场景选择。'
  },
  {
    icon: Medal,
    title: '求职持续陪跑',
    desc: '记录历次面试表现，生成成长曲线，见证你的每一次进步与突破。'
  }
];
</script>

<style scoped>
.landing {
  min-height: 100vh;
  background-color: #fafafa; /* Slightly deeper than pure white for contrast */
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

/* --- Header --- */
.landing-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 5%;
  height: 80px;
  z-index: 100;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(229, 231, 235, 0.8);
  transition: all 0.3s ease;
  box-shadow: 0 4px 20px -10px rgba(0,0,0,0.05); /* Adds a subtle lift to header */
}

.header-left {
  display: flex;
  align-items: center;
  gap: 80px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 22px;
  font-weight: 800;
  color: #111827;
  letter-spacing: -0.5px;
}
.logo-icon {
  color: #111827;
  font-size: 24px;
}

.picture-logo {
  position: absolute;
  left: 230px;
}
@media (max-width: 1024px) {
  .picture-logo {
    display: none;
  }
}

/* --- Redesigned Nav Links --- */
.nav-links-container {
  display: none;
  margin-left: 20px;
}
@media (min-width: 768px) {
  .nav-links-container {
    display: flex;
  }
}
.nav-links {
  display: flex;
  background: #f3f4f6;
  padding: 4px;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.02);
}
.nav-links a {
  color: #6b7280;
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
  padding: 6px 20px;
  border-radius: 999px;
  transition: all 0.2s ease;
}
.nav-links a.active, .nav-links a:hover {
  background: #ffffff;
  color: #111827;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.04);
}

.actions {
  display: flex;
  gap: 12px;
  align-items: center;
}
.login-btn {
  color: #4b5563;
  font-weight: 600;
  font-size: 14px;
}
.login-btn:hover {
  color: #111827;
  background: transparent;
}
.register-btn {
  background: linear-gradient(180deg, #1f2937, #000000);
  border: 1px solid #000000;
  color: #ffffff;
  font-weight: 600;
  font-size: 14px;
  padding: 8px 18px;
  border-radius: 8px; /* Slightly softer corners for premium feel */
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.1);
}
.register-btn:hover {
  background: #333333;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

/* --- Main Content --- */
.landing-main {
  position: relative;
  z-index: 10;
  padding-top: 80px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* --- Hero Section --- */
.hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 1280px;
  padding: 80px 40px;
  margin: 0 auto;
}
@media (min-width: 1024px) {
  .hero {
    flex-direction: row;
    justify-content: space-between;
    padding: 120px 40px;
  }
}

.hero-content {
  flex: 1;
  max-width: 540px;
}

.title {
  font-size: 56px;
  line-height: 1.15;
  font-weight: 800;
  margin-bottom: 24px;
  letter-spacing: -1.5px;
  color: #111827;
}
@media (max-width: 768px) {
  .title {
    font-size: 42px;
  }
}
.highlight {
  background: linear-gradient(135deg, #a855f7 0%, #7e22ce 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  display: block;
  margin-top: 8px;
}

.subtitle {
  font-size: 18px;
  line-height: 1.6;
  color: #4b5563;
  margin-bottom: 40px;
  font-weight: 400;
}

.hero-actions {
  display: flex;
  gap: 16px;
  margin-bottom: 60px;
  flex-wrap: wrap;
}

.start-btn {
  background: linear-gradient(180deg, #1f2937, #000000);
  border: 1px solid #000000;
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  padding: 12px 32px;
  border-radius: 8px;
  height: 48px;
  transition: all 0.2s ease;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.1);
}
.start-btn:hover {
  background: #333333;
  transform: translateY(-2px);
  box-shadow: 0 8px 15px rgba(0,0,0,0.15);
}

.stats {
  display: flex;
  align-items: center;
  gap: 32px;
  flex-wrap: wrap;
}
.stat-item {
  display: flex;
  flex-direction: column;
}
.stat-num {
  font-size: 20px;
  font-weight: 800;
  color: #111827;
}
.stat-desc {
  font-size: 13px;
  color: #6b7280;
  margin-top: 4px;
  font-weight: 500;
}
.stat-divider {
  width: 1px;
  height: 32px;
  background: #e5e7eb;
}

/* --- Hero Visual --- */
.hero-visual {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
  margin-top: 60px;
  width: 100%;
}
@media (min-width: 1024px) {
  .hero-visual {
    margin-top: 0;
    margin-left: 60px;
    justify-content: flex-end;
  }
}

.mock-window {
  width: 100%;
  max-width: 500px;
  background: #ffffff;
  border: 1px solid rgba(229, 231, 235, 0.8);
  border-radius: 12px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.1), 0 0 0 1px rgba(0,0,0,0.02);
  overflow: hidden;
  position: relative;
}

.window-header {
  height: 36px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 8px;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);
}
.dot.red { background: #ef4444; }
.dot.yellow { background: #eab308; }
.dot.green { background: #22c55e; }

.window-body {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  background: #fafafa;
}

.ai-chat {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chat-msg {
  padding: 14px 18px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.5;
  max-width: 85%;
  box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}

.chat-msg.ai {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  color: #374151;
  align-self: flex-start;
  border-bottom-left-radius: 2px;
}

.chat-msg.user {
  background: linear-gradient(135deg, #1f2937, #111827);
  color: #ffffff;
  align-self: flex-end;
  border-bottom-right-radius: 2px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

.style-typing {
  position: relative;
  padding-right: 20px;
}
.style-typing::after {
  content: '';
  position: absolute;
  width: 4px;
  height: 14px;
  background: rgba(255, 255, 255, 0.8);
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.analysis-card {
  background: #ffffff;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}
.card-title {
  font-size: 12px;
  font-weight: 700;
  color: #6b7280;
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.card-desc {
  font-size: 13px;
  color: #4b5563;
  margin-top: 12px;
  line-height: 1.5;
}

.float-card {
  position: absolute;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(229, 231, 235, 0.8);
  padding: 12px 20px;
  border-radius: 12px;
  display: none;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 15px 30px -5px rgba(0, 0, 0, 0.1);
  color: #111827;
}
@media (min-width: 768px) {
  .float-card {
    display: flex;
  }
}

.card-1 {
  bottom: -20px;
  left: -40px;
  animation: float-y 6s ease-in-out infinite reverse;
}

@keyframes float-y {
  0% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
  100% { transform: translateY(0); }
}

.float-card .icon {
  font-size: 18px;
  color: #9333ea;
  background: rgba(147, 51, 234, 0.1);
  padding: 8px;
  border-radius: 8px;
}

/* --- Features Section --- */
.features {
  width: 100%;
  max-width: 1280px;
  padding: 80px 40px;
  margin: 0 auto;
}

.section-title {
  text-align: center;
  font-size: 32px;
  font-weight: 800;
  margin-bottom: 60px;
  letter-spacing: -0.5px;
  color: #111827;
}

.feature-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 32px;
}
@media (min-width: 768px) {
  .feature-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (min-width: 1024px) {
  .feature-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* Feature Cards Texture Updates */
.feature-card {
  position: relative;
  background: linear-gradient(145deg, #ffffff 0%, #f9fafb 100%);
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  padding: 32px;
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02), inset 0 1px 0 rgba(255, 255, 255, 1);
  overflow: hidden;
}

.feature-card::after {
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

.feature-card:hover {
  border-color: rgba(168, 85, 247, 0.3);
  box-shadow: 0 20px 40px -10px rgba(147, 51, 234, 0.1), inset 0 1px 0 rgba(255, 255, 255, 1);
  transform: translateY(-6px);
}
.feature-card:hover::after {
  opacity: 1;
}

.feature-card .icon-wrapper {
  width: 52px;
  height: 52px;
  background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: #6b7280;
  margin-bottom: 20px;
  transition: all 0.3s ease;
  box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.8), 0 2px 4px rgba(0, 0, 0, 0.02);
}
.feature-card:hover .icon-wrapper {
  background: linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(147, 51, 234, 0.05) 100%);
  color: #9333ea;
  border-color: rgba(168, 85, 247, 0.2);
}

.feature-card h3 {
  font-size: 19px;
  font-weight: 800;
  margin-bottom: 12px;
  color: #111827;
}
.feature-card p {
  font-size: 14px;
  line-height: 1.6;
  color: #4b5563;
}

/* --- Trust/Logos Section --- */
.trust-section {
  width: 100%;
  max-width: 1280px;
  margin: 0 auto 100px;
  padding: 0 40px;
  text-align: center;
  border-top: 1px solid #e5e7eb;
  padding-top: 60px;
}
.trust-title {
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 32px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.trust-logos {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 40px;
  flex-wrap: wrap;
  opacity: 0.5;
  transition: opacity 0.3s ease;
}
.trust-logos:hover {
  opacity: 0.8;
}
.trust-brand {
  font-size: 22px;
  font-weight: 800;
  color: #6b7280;
  letter-spacing: 1.5px;
  text-transform: uppercase;
}

/* Custom Element Plus variables override */
:deep(.el-progress-bar__outer) {
  background-color: #f3f4f6 !important;
}
:deep(.el-progress__text) {
  color: #111827 !important;
  font-weight: 700;
  font-size: 13px !important;
}
</style>