const express = require('express');
const cors = require('cors');
const jwt = require('jsonwebtoken');
const fs = require('fs');
const path = require('path');
const multer = require('multer');
const crypto = require('crypto');
const pool = require('./db');

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret-key';

const app = express();
const PORT = process.env.PORT || 3000;

// 头像上传目录
const AVATAR_DIR = path.join(__dirname, 'uploads', 'avatar');
if (!fs.existsSync(AVATAR_DIR)) {
  fs.mkdirSync(AVATAR_DIR, { recursive: true });
}

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, AVATAR_DIR),
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname || '') || '.png';
    const userId = (req.user && req.user.id) || 'guest';
    cb(null, `avatar_${userId}_${Date.now()}${ext}`);
  },
});

const upload = multer({
  storage,
  limits: { fileSize: 2 * 1024 * 1024 },
});

// 面试简历上传目录（PDF/Word，与头像分开）
const INTERVIEW_RESUME_DIR = path.join(__dirname, 'uploads', 'interview-resume');
if (!fs.existsSync(INTERVIEW_RESUME_DIR)) {
  fs.mkdirSync(INTERVIEW_RESUME_DIR, { recursive: true });
}
const resumeStorage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, INTERVIEW_RESUME_DIR),
  filename: (req, file, cb) => {
    const uid = (req.user && req.user.id) || 'guest';
    const id = `${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
    const ext = path.extname(file.originalname || '') || '';
    cb(null, `resume_${uid}_${id}${ext}`);
  },
});
const uploadInterviewResume = multer({
  storage: resumeStorage,
  limits: { fileSize: 5 * 1024 * 1024 },
});
// 语音回答上传：仅做内存解析，不落盘（与 FastAPI 的 UploadFile.read() 语义一致）
const uploadInterviewVoice = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 20 * 1024 * 1024 },
});

/**
 * 豆包（火山方舟）OpenAPI：POST chat/completions
 * - ARK_API_KEY：API Key（必填，走真实流式）
 * - ARK_ENDPOINT_ID：推理接入点 ID，即请求体里的 model（如 ep-xxxx，必填）
 * - ARK_CHAT_URL：可选，默认 https://ark.cn-beijing.volces.com/api/v3/chat/completions
 * 兼容旧变量：DOUBAO_API_KEY / DOUBAO_ENDPOINT_ID
 */
const ARK_API_KEY =
  '2fa1baf7-49f1-4c32-8f53-d759d4a1b336'
const ARK_ENDPOINT_ID =
 'doubao-seed-2-0-code-preview-260215'
const ARK_CHAT_COMPLETIONS_URL =
  process.env.ARK_CHAT_URL ||
  'https://ark.cn-beijing.volces.com/api/v3/chat/completions';
const AVATAR_VENDOR = process.env.AVATAR_VENDOR || 'mock-xnrpt';
const AVATAR_TOKEN_TTL_SEC = Number(process.env.AVATAR_TOKEN_TTL_SEC || 300);
const AVATAR_APP_ID = process.env.AVATAR_APP_ID || '';
// 仅后端使用：用于生成 signedUrl / token，禁止下发前端
const AVATAR_API_KEY = process.env.AVATAR_API_KEY || '';
const AVATAR_API_SECRET = process.env.AVATAR_API_SECRET || '';
const AVATAR_SCENE_ID = process.env.AVATAR_SCENE_ID || '';
const AVATAR_VCN = process.env.AVATAR_VCN || '';
const AVATAR_SERVER_URL = process.env.AVATAR_SERVER_URL || 'wss://avatar.cn-huadong-1.xf-yun.com/v1/interact';
const AVATAR_ALLOWED_IDS = new Set(['110592024', '110117005', '110017006']);

// AI 面试会话：内存存储，进程重启后清空
// sessionId -> { userId, interviewMode, messages: [{role, content}], updatedAt }
const interviewAiSessions = new Map();
// 新版面试会话（按用户提供的新接口协议）
// session_id -> { userId, resume, position, collection_name, status, total_rounds, current_topic, current_question, history }
const interviewSessionsV2 = new Map();
// 虚拟人会话（方案A：后端签发短时凭证，前端直连流媒体）
// session_id -> { userId, avatar_session_id, avatar_id, token, expire_at, stream_url, ws_url, status }
const avatarInterviewSessions = new Map();
const AI_INTERVIEW_MAX_QUESTIONS = Number(process.env.AI_INTERVIEW_MAX_QUESTIONS || 10);
/** 模拟新版面试：超过该轮次后结束会话并下发 interview_complete，便于联调「面试报告」 */
const INTERVIEW_MOCK_MAX_ROUNDS = Number(process.env.INTERVIEW_MOCK_MAX_ROUNDS || 8);
const AI_INTERVIEW_SCORE_MIN = Number(process.env.AI_INTERVIEW_SCORE_MIN || 0);
const AI_INTERVIEW_SCORE_MAX = Number(process.env.AI_INTERVIEW_SCORE_MAX || 10);

function buildInterviewSystemPrompt(ctx) {
  const resumeLine = ctx.resumeOriginalName
    ? `候选人已上传简历文件：${ctx.resumeOriginalName}（服务端仅存文件，暂不解析正文）。`
    : '候选人未上传简历或选择跳过简历。';
  return `你是一名专业、友善的技术面试官，正在模拟真实面试场景。
请根据以下候选人信息进行提问与追问，语言简洁专业，每次回复控制在合理长度。

【岗位】${ctx.positionName || '未填写'}
【薪资预期】${ctx.salaryExpected || '未填写'}
【公司名称】${ctx.companyName || '未填写'}
【工作内容 / JD 摘要】
${ctx.jobContent || '未填写'}

${resumeLine}

面试模式说明：当前为「${ctx.interviewMode === 'voice' ? '语音面试（占位，仍按文本交互说明）' : '文本面试'}」。请一次只问 1～2 个相关问题，或针对候选人上一句回答做简短点评后再追问。`;
}

function ok200(data = null, message = 'success') {
  return { code: 200, message, data };
}

function inferTopicByText(text) {
  if (!text) return '通用技术能力';
  const t = String(text);
  if (/性能|卡顿|优化/.test(t)) return '前端性能优化\n用户体验设计';
  if (/并发|异步|协程|RxJava/.test(t)) return 'Android异步并发管理';
  if (/架构|组件|模块/.test(t)) return '架构设计与模块拆分';
  return '项目经验分析\n技术问题解决';
}

function extractJsonObject(text) {
  const raw = String(text || '').trim();
  const start = raw.indexOf('{');
  const end = raw.lastIndexOf('}');
  if (start === -1 || end === -1 || end <= start) return null;
  try {
    return JSON.parse(raw.slice(start, end + 1));
  } catch (_e) {
    return null;
  }
}

function buildAvatarToken() {
  return crypto.randomBytes(20).toString('hex');
}

function buildAvatarSignedUrl(serverUrl, apiKey, apiSecret) {
  if (!serverUrl || !apiKey || !apiSecret) return '';
  try {
    const u = new URL(serverUrl);
    const host = u.host;
    const path = u.pathname || '/';
    const date = new Date().toUTCString();
    const signatureOrigin = `host: ${host}\ndate: ${date}\nGET ${path} HTTP/1.1`;
    const signatureSha = crypto
      .createHmac('sha256', apiSecret)
      .update(signatureOrigin, 'utf8')
      .digest('base64');
    const authorizationOrigin = `api_key="${apiKey}", algorithm="hmac-sha256", headers="host date request-line", signature="${signatureSha}"`;
    const authorization = Buffer.from(authorizationOrigin, 'utf8').toString('base64');
    const qs = new URLSearchParams({
      authorization,
      date,
      host,
    }).toString();
    return `${u.origin}${path}?${qs}`;
  } catch (_e) {
    return '';
  }
}

function buildAvatarSdkConfig(_session_id, _avatar_session_id, token, expire_at) {
  const signed_url = buildAvatarSignedUrl(AVATAR_SERVER_URL, AVATAR_API_KEY, AVATAR_API_SECRET);
  return {
    app_id: AVATAR_APP_ID,
    has_server_auth_config: Boolean(AVATAR_API_KEY && AVATAR_API_SECRET),
    server_url: AVATAR_SERVER_URL,
    signed_url,
    scene_id: AVATAR_SCENE_ID,
    vcn: AVATAR_VCN,
    protocol: 'xrtc',
    alpha: 1,
    token,
    expire_at,
  };
}

async function callArkChatOnce(messages) {
  if (!ARK_API_KEY || !ARK_ENDPOINT_ID) return '';
  try {
    const upstream = await fetch(ARK_CHAT_COMPLETIONS_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${ARK_API_KEY}`,
      },
      body: JSON.stringify({
        model: ARK_ENDPOINT_ID,
        stream: false,
        messages,
      }),
    });
    if (!upstream.ok) return '';
    const data = await upstream.json();
    return (
      data &&
      data.choices &&
      data.choices[0] &&
      data.choices[0].message &&
      String(data.choices[0].message.content || '')
    );
  } catch (_e) {
    return '';
  }
}

/** 无 API Key 时的模拟流式输出 */
async function writeMockStream(res, fullText) {
  const chunks = fullText.split(/(?=[。！？\n])|(?<=。)|(?<=！)|(?<=？)/).filter(Boolean);
  const useChunks = chunks.length > 1 ? chunks : [fullText];
  for (const c of useChunks) {
    for (const ch of c) {
      res.write(`data: ${JSON.stringify({ content: ch })}\n\n`);
      // eslint-disable-next-line no-await-in-loop
      await new Promise((r) => setTimeout(r, 8));
    }
  }
}

/**
 * 创建会话时生成 AI 首问：
 * 1) 已配置方舟参数时，优先调用豆包（非流式）
 * 2) 失败或未配置时，回退到本地模板
 */
async function generateOpeningQuestion({ systemContent, positionName, mode }) {
  // 语音模式当前仍为占位文案
  if (mode === 'voice') {
    return '欢迎来到语音面试（占位模式）。当前版本先不做语音识别与情感分析，您可以先切换文本模式体验。';
  }

  const fallback =
    `你好，我是本次面试官。我们先从自我介绍开始：请你用 1-2 分钟介绍一下你与「${positionName}」最相关的项目经历与技术亮点。`;

  if (!ARK_API_KEY || !ARK_ENDPOINT_ID) {
    return fallback;
  }

  try {
    const upstream = await fetch(ARK_CHAT_COMPLETIONS_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${ARK_API_KEY}`,
      },
      body: JSON.stringify({
        model: ARK_ENDPOINT_ID,
        stream: false,
        messages: [
          { role: 'system', content: systemContent },
          {
            role: 'user',
            content:
              '请你作为面试官先手发起第一问。要求：1）只输出一段自然中文提问；2）不超过120字；3）紧贴候选人目标岗位；4）不要输出前缀标题。',
          },
        ],
      }),
    });

    if (!upstream.ok) {
      const errText = await upstream.text().catch(() => upstream.statusText);
      console.error('生成首问失败（豆包）:', upstream.status, errText);
      return fallback;
    }

    const data = await upstream.json();
    const content =
      data &&
      data.choices &&
      data.choices[0] &&
      data.choices[0].message &&
      data.choices[0].message.content;
    const opening = content ? String(content).trim() : '';
    return opening || fallback;
  } catch (e) {
    console.error('生成首问异常（豆包）:', e);
    return fallback;
  }
}

function safeJsonParse(raw) {
  try {
    return JSON.parse(raw);
  } catch (_e) {
    return null;
  }
}

async function scoreInterviewAnswer({ systemContent, question, answer }) {
  const fallback = { score: 6, comment: '回答基本完整，建议增加量化结果与技术细节。' };
  if (!ARK_API_KEY || !ARK_ENDPOINT_ID) return fallback;
  try {
    const upstream = await fetch(ARK_CHAT_COMPLETIONS_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${ARK_API_KEY}`,
      },
      body: JSON.stringify({
        model: ARK_ENDPOINT_ID,
        stream: false,
        messages: [
          { role: 'system', content: systemContent },
          {
            role: 'user',
            content: `请对候选人回答评分（满分10分）。只输出 JSON：{"score": number, "comment": "一句话点评"}。\n上一个问题：${question}\n候选人回答：${answer}`,
          },
        ],
      }),
    });
    if (!upstream.ok) return fallback;
    const data = await upstream.json();
    const content =
      data &&
      data.choices &&
      data.choices[0] &&
      data.choices[0].message &&
      data.choices[0].message.content;
    const parsed = safeJsonParse(String(content || '').trim());
    if (!parsed || typeof parsed.score !== 'number') return fallback;
    return {
      score: Number(parsed.score),
      comment: parsed.comment ? String(parsed.comment) : '',
    };
  } catch (_e) {
    return fallback;
  }
}

async function buildInterviewReportContent({ positionName, rounds, avgScore, scoreComments }) {
  const fallback = {
    totalScore: Math.max(0, Math.min(10, Number(avgScore.toFixed(1)))),
    dimensions: [
      { name: '表达与沟通', score: Math.max(0, Math.min(10, Math.round(avgScore))), comment: '表达较清晰，建议更结构化。' },
      { name: '技术深度', score: Math.max(0, Math.min(10, Math.round(avgScore))), comment: '有一定技术细节，可补充性能与权衡。' },
      { name: '问题解决', score: Math.max(0, Math.min(10, Math.round(avgScore))), comment: '能描述解决思路，建议增加复盘。' },
    ],
    summary: `本次模拟面试已完成，共 ${rounds} 轮问答，综合表现中等偏上。`,
    suggestions: [
      '使用 STAR 结构回答项目问题（背景、任务、行动、结果）',
      '补充量化结果，如性能提升百分比、故障率下降等',
      '回答中增加技术权衡与取舍说明',
    ],
  };
  if (!ARK_API_KEY || !ARK_ENDPOINT_ID) return fallback;
  try {
    const upstream = await fetch(ARK_CHAT_COMPLETIONS_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${ARK_API_KEY}`,
      },
      body: JSON.stringify({
        model: ARK_ENDPOINT_ID,
        stream: false,
        messages: [
          {
            role: 'user',
            content:
              `你是面试评审官。基于以下信息生成面试报告 JSON，不要输出额外文字。` +
              `格式：{"totalScore":number,"dimensions":[{"name":"表达与沟通","score":number,"comment":"..."},{"name":"技术深度","score":number,"comment":"..."},{"name":"问题解决","score":number,"comment":"..."}],"summary":"...","suggestions":["...","..."]}` +
              `岗位：${positionName || '未填写'}；轮次：${rounds}；平均分：${avgScore.toFixed(1)}；评分点评：${scoreComments.join(' | ')}`,
          },
        ],
      }),
    });
    if (!upstream.ok) return fallback;
    const data = await upstream.json();
    const content =
      data &&
      data.choices &&
      data.choices[0] &&
      data.choices[0].message &&
      data.choices[0].message.content;
    const parsed = safeJsonParse(String(content || '').trim());
    if (!parsed || typeof parsed !== 'object') return fallback;
    return {
      totalScore:
        typeof parsed.totalScore === 'number' ? Math.max(0, Math.min(10, parsed.totalScore)) : fallback.totalScore,
      dimensions: Array.isArray(parsed.dimensions) ? parsed.dimensions : fallback.dimensions,
      summary: parsed.summary ? String(parsed.summary) : fallback.summary,
      suggestions: Array.isArray(parsed.suggestions) ? parsed.suggestions : fallback.suggestions,
    };
  } catch (_e) {
    return fallback;
  }
}

// 简单的验证码存储（仅用于演示环境，进程重启后会丢失）
// key 形如：register:email 或 reset:username
const verifyCodes = new Map();
const CODE_EXPIRE_MS = 10 * 60 * 1000; // 10 分钟

function genCode() {
  return String(Math.floor(100000 + Math.random() * 900000));
}

function setCode(key) {
  const code = genCode();
  verifyCodes.set(key, { code, expiresAt: Date.now() + CODE_EXPIRE_MS });
  return code;
}

function checkCode(key, code) {
  const item = verifyCodes.get(key);
  if (!item) return false;
  if (Date.now() > item.expiresAt) {
    verifyCodes.delete(key);
    return false;
  }
  const okMatch = String(code).trim() === String(item.code);
  if (okMatch) {
    verifyCodes.delete(key);
  }
  return okMatch;
}

// 根据相对路径生成完整可访问的头像链接；如无则返回默认头像链接
function buildAvatarUrl(req, avatarPath) {
  const base = `${req.protocol}://${req.get('host')}`;
  const pathOrDefault = avatarPath || '/avatar-file/default-avatar.png';
  if (pathOrDefault.startsWith('http')) return pathOrDefault;
  return base + pathOrDefault;
}

app.use(cors());
app.use(express.json({ limit: '5mb' }));
// 兼容无 /api 前缀请求：将 /auth/*、/interview/* 等自动映射到 /api/*
app.use((req, _res, next) => {
  if (req.url === '/api' || req.url.startsWith('/api/')) return next();
  if (req.url === '/avatar-file' || req.url.startsWith('/avatar-file/')) return next();
  req.url = `/api${req.url.startsWith('/') ? req.url : `/${req.url}`}`;
  next();
});
// 管理后台文档前缀 `/admin/*`：与真实后端一致，转发到现有 `/api/users`、`/api/roles`、`/api/positions` 处理器
app.use((req, _res, next) => {
  if (req.url.startsWith('/api/admin/users')) {
    req.url = req.url.replace(/^\/api\/admin\/users/, '/api/users');
  } else if (req.url.startsWith('/api/admin/roles')) {
    req.url = req.url.replace(/^\/api\/admin\/roles/, '/api/roles');
  } else if (req.url.startsWith('/api/admin/positions')) {
    req.url = req.url.replace(/^\/api\/admin\/positions/, '/api/positions');
  }
  next();
});
// 对外暴露头像静态文件
app.use('/api/avatar-file', express.static(AVATAR_DIR));
app.use('/avatar-file', express.static(AVATAR_DIR));

function ok(data = null, message = 'ok') {
  return { code: 0, message, data };
}
function fail(code, message) {
  return { code, message, data: null };
}

// 验证 token，写入 req.user（含 id, username, roleId）
function authMiddleware(req, res, next) {
  const authHeader = req.headers.authorization || '';
  const token = authHeader.replace(/^Bearer\s+/i, '');
  if (!token) {
    return res.status(401).json(fail(401, '未提供 token'));
  }
  try {
    const payload = jwt.verify(token, JWT_SECRET);
    req.user = payload;
    next();
  } catch (e) {
    return res.status(401).json(fail(401, 'token 无效或已过期'));
  }
}

// 需要管理员角色（假定 roleId 2 为管理员）
function adminMiddleware(req, res, next) {
  if (req.user.roleId !== 2) {
    return res.status(403).json(fail(403, '无权限'));
  }
  next();
}

// ----- 认证 -----

// 用户注册
app.post('/api/auth/register', async (req, res) => {
  const { username, password, confirmPassword, email, emailCode } = req.body || {};
  if (!username || !password || !confirmPassword) {
    return res.json(fail(1001, '用户名或密码不能为空'));
  }
  if (password !== confirmPassword) {
    return res.json(fail(1002, '两次密码不一致'));
  }
  // 如果填写了邮箱，则需要验证码校验
  if (email) {
    if (!emailCode) {
      return res.json(fail(400, '请先完成邮箱验证码验证'));
    }
    const okMatch = checkCode(`register:${email}`, emailCode);
    if (!okMatch) {
      return res.json(fail(1009, '验证码错误或已过期'));
    }
  }
  try {
    const [rows] = await pool.query('SELECT id FROM `user` WHERE username = ?', [username]);
    if (rows.length > 0) {
      return res.json(fail(1003, '用户名已存在'));
    }
    await pool.query('INSERT INTO `user` (username, password, email, role_id) VALUES (?, ?, ?, 1)', [
      username,
      password,
      email || null,
    ]);
    return res.json(ok(null, '注册成功'));
  } catch (err) {
    console.error('注册失败:', err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// 用户登录
app.post('/api/auth/login', async (req, res) => {
  const { username, password } = req.body || {};
  if (!username || !password) {
    return res.json(fail(1001, '用户名或密码不能为空'));
  }
  try {
    const [rows] = await pool.query(
      'SELECT u.id, u.username, u.role_id, u.avatar_url, r.name AS role_name FROM `user` u JOIN role r ON u.role_id = r.id WHERE u.username = ? AND u.password = ?',
      [username, password]
    );
    if (rows.length === 0) {
      return res.json(fail(1004, '用户名或密码错误'));
    }
    const row = rows[0];
    const token = jwt.sign(
      { id: String(row.id), username: row.username, roleId: row.role_id },
      JWT_SECRET,
      { expiresIn: '2h' }
    );
    const avatarUrl = buildAvatarUrl(req, row.avatar_url);
    return res.json(
      ok({
        token,
        user: {
          id: String(row.id),
          username: row.username,
          roleId: row.role_id,
          roleName: row.role_name,
          avatarUrl,
        },
      })
    );
  } catch (err) {
    console.error('登录失败:', err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// 获取当前用户信息
app.get('/api/auth/profile', authMiddleware, async (req, res) => {
  const { id } = req.user;
  try {
    const [rows] = await pool.query(
      'SELECT u.id, u.username, u.email, u.avatar_url, u.role_id, r.name AS role_name FROM `user` u JOIN role r ON u.role_id = r.id WHERE u.id = ?',
      [id]
    );
    if (rows.length === 0) {
      return res.json(fail(1005, '用户不存在'));
    }
    const u = rows[0];
    const avatarUrl = buildAvatarUrl(req, u.avatar_url);
    return res.json(
      ok({
        id: String(u.id),
        username: u.username,
        email: u.email || undefined,
        roleId: u.role_id,
        roleName: u.role_name,
        avatarUrl,
      })
    );
  } catch (err) {
    console.error('获取用户信息失败:', err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// 发送验证码（注册绑定邮箱 / 找回密码）
app.post('/api/auth/send-code', async (req, res) => {
  const { scene, username, email } = req.body || {};

  if (scene === 'register') {
    if (!email) return res.json(fail(400, '邮箱不能为空'));
    const key = `register:${email}`;
    const code = setCode(key);
    console.log(`[验证码][注册] email=${email}, code=${code}`);
    return res.json(ok(null, '验证码已发送'));
  }

  // 默认视为找回密码
  if (!username) return res.json(fail(400, '用户名不能为空'));
  try {
    const [rows] = await pool.query('SELECT id, email FROM `user` WHERE username = ?', [username]);
    if (rows.length === 0) return res.json(fail(1005, '用户不存在'));
    let userEmail = rows[0].email;

    if (!userEmail) {
      if (!email) {
        return res.json(fail(400, '邮箱未绑定，请先绑定邮箱'));
      }
      // 简单处理：在找回密码流程中顺便绑定邮箱
      await pool.query('UPDATE `user` SET email = ? WHERE id = ?', [email, rows[0].id]);
      userEmail = email;
    }

    const key = `reset:${username}`;
    const code = setCode(key);
    console.log(`[验证码][找回密码] username=${username}, email=${userEmail}, code=${code}`);
    return res.json(ok(null, '验证码已发送'));
  } catch (err) {
    console.error('发送验证码失败:', err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// 找回密码：验证验证码并重置密码
app.post('/api/auth/verify-code', async (req, res) => {
  const { username, code, newPassword, confirmPassword } = req.body || {};
  if (!username) return res.json(fail(400, '用户名不能为空'));
  if (!code) return res.json(fail(1008, '验证码不能为空'));
  if (!newPassword || !confirmPassword) return res.json(fail(1010, '密码不能为空'));
  if (newPassword !== confirmPassword) return res.json(fail(1002, '两次密码不一致'));

  try {
    const [rows] = await pool.query('SELECT id FROM `user` WHERE username = ?', [username]);
    if (rows.length === 0) return res.json(fail(1005, '用户不存在'));

    const key = `reset:${username}`;
    const okMatch = checkCode(key, code);
    if (!okMatch) return res.json(fail(1009, '验证码错误或已过期'));

    await pool.query('UPDATE `user` SET password = ? WHERE id = ?', [newPassword, rows[0].id]);
    return res.json(ok(null, '密码重置成功'));
  } catch (err) {
    console.error('重置密码失败:', err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// 修改密码（需登录 + 邮箱验证码）
app.post('/api/auth/password', authMiddleware, async (req, res) => {
  const { oldPassword, newPassword, confirmPassword, code } = req.body || {};
  if (!oldPassword || !newPassword || !confirmPassword) {
    return res.json(fail(1010, '密码不能为空'));
  }
  if (newPassword !== confirmPassword) {
    return res.json(fail(1002, '两次新密码不一致'));
  }
  if (!code) {
    return res.json(fail(1008, '验证码不能为空'));
  }

  const userId = req.user.id;
  const username = req.user.username;

  try {
    const [rows] = await pool.query('SELECT password FROM `user` WHERE id = ?', [userId]);
    if (rows.length === 0) return res.json(fail(1005, '用户不存在'));
    if (rows[0].password !== oldPassword) {
      return res.json(fail(1006, '原密码错误'));
    }

    const okMatch = checkCode(`reset:${username}`, code);
    if (!okMatch) {
      return res.json(fail(1009, '验证码错误或已过期'));
    }

    await pool.query('UPDATE `user` SET password = ? WHERE id = ?', [newPassword, userId]);
    return res.json(ok(null, '密码修改成功'));
  } catch (err) {
    console.error('修改密码失败:', err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// 上传 / 修改头像（支持 multipart/form-data 和 base64 JSON）
app.post('/api/auth/avatar', authMiddleware, upload.single('file'), async (req, res) => {
  const { id } = req.user;
  try {
    let avatarUrl = null;

    if (req.file) {
      // 表单上传文件
      avatarUrl = `/avatar-file/${req.file.filename}`;
    } else if (req.body && req.body.avatar) {
      // base64 字符串
      const base64 = req.body.avatar;
      const match = base64.match(/^data:image\/\w+;base64,(.+)$/);
      const data = match ? match[1] : base64;
      const buf = Buffer.from(data, 'base64');
      const filename = `avatar_${id}_${Date.now()}.png`;
      const filepath = path.join(AVATAR_DIR, filename);
      fs.writeFileSync(filepath, buf);
      avatarUrl = `/avatar-file/${filename}`;
    } else {
      return res.json(fail(400, '请上传文件或提供 avatar 字段'));
    }

    await pool.query('UPDATE `user` SET avatar_url = ? WHERE id = ?', [avatarUrl, id]);

    const fullUrl = buildAvatarUrl(req, avatarUrl);

    return res.json(ok({ avatarUrl: fullUrl }));
  } catch (err) {
    console.error('上传头像失败:', err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 角色 -----
app.get('/api/roles', authMiddleware, async (req, res) => {
  try {
    const [rows] = await pool.query('SELECT id, name FROM role ORDER BY id');
    return res.json(ok(rows.map((r) => ({ id: r.id, name: r.name }))));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 岗位 -----
// 额外岗位字段的内存存储（仅用于模拟环境，不入库）
// key: positionId, value: { city, workExperience, ... }
const positionExtras = new Map();
app.get('/api/positions', authMiddleware, async (req, res) => {
  try {
    const [rows] = await pool.query('SELECT id, name, sort_order AS sortOrder FROM `position` ORDER BY sort_order, id');
    // 将内存中的扩展字段合并到列表中，方便后台管理表单回显
    const list = rows.map((r) => {
      const extra = positionExtras.get(r.id) || {};
      return { ...r, ...extra };
    });
    return res.json(ok(list));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.get('/api/positions/:id', authMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    const [rows] = await pool.query('SELECT id, name, sort_order AS sortOrder FROM `position` WHERE id = ?', [id]);
    if (rows.length === 0) return res.status(404).json(fail(404, '岗位不存在'));

    const row = rows[0];
    const extra = positionExtras.get(row.id) || {};

    /**
     * 为了配合后台管理系统展示更丰富的岗位详情，这里在原有基础结构上
     * 额外返回一组“模拟字段”。这些字段可以通过 GET 查询参数覆盖，
     * 方便在本地调试不同文案，而无需真正修改数据库。
     *
     * 例如：
     *   GET /api/positions/1?city=上海&salaryMin=30000&salaryMax=50000
     */
    const q = req.query || {};

    const detail = {
      // 原有结构（保持兼容）
      id: row.id,
      name: row.name,
      sortOrder: row.sortOrder,
      // 扩展的模拟字段，用于岗位详情展示（优先使用已保存的值，其次是查询参数，最后是默认值）
      city: q.city || extra.city || '北京',
      workExperience: q.workExperience || extra.workExperience || '3-5 年',
      education: q.education || extra.education || '本科及以上',
      salaryMin:
        q.salaryMin !== undefined
          ? Number(q.salaryMin)
          : extra.salaryMin !== undefined
          ? Number(extra.salaryMin)
          : 20000,
      salaryMax:
        q.salaryMax !== undefined
          ? Number(q.salaryMax)
          : extra.salaryMax !== undefined
          ? Number(extra.salaryMax)
          : 40000,
      responsibilities:
        q.responsibilities ||
        extra.responsibilities ||
        '1. 负责 Web 前端需求分析与开发；2. 与产品和后端配合，持续优化用户体验；3. 推动前端工程化与性能优化。',
      requirements:
        q.requirements ||
        extra.requirements ||
        '1. 熟悉 HTML5/CSS3/JavaScript；2. 至少掌握一种前端框架（如 Vue/React）；3. 良好的编码习惯与沟通协作能力。',
      tags:
        (q.tags &&
          String(q.tags)
            .split(',')
            .map((t) => t.trim())
            .filter(Boolean)) ||
        extra.tags ||
        ['前端', '面试', '高薪'],
      publishDate: q.publishDate || extra.publishDate || new Date().toISOString(),
    };

    return res.json(ok(detail));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.post('/api/positions', authMiddleware, adminMiddleware, async (req, res) => {
  const {
    name,
    sortOrder,
    city,
    workExperience,
    education,
    salaryMin,
    salaryMax,
    responsibilities,
    requirements,
    tags,
    publishDate,
  } = req.body || {};
  if (!name) return res.json(fail(400, '岗位名称不能为空'));
  try {
    const [r] = await pool.query('INSERT INTO `position` (name, sort_order) VALUES (?, ?)', [name, sortOrder ?? 0]);
    const id = r.insertId;
    // 在内存中保存扩展字段（不影响数据库结构）
    positionExtras.set(id, {
      city,
      workExperience,
      education,
      salaryMin,
      salaryMax,
      responsibilities,
      requirements,
      tags,
      publishDate,
    });
    return res.json(
      ok({
        id,
        name,
        sortOrder: sortOrder ?? 0,
        city,
        workExperience,
        education,
        salaryMin,
        salaryMax,
        responsibilities,
        requirements,
        tags,
        publishDate,
      })
    );
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.put('/api/positions/:id', authMiddleware, adminMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  const {
    name,
    sortOrder,
    city,
    workExperience,
    education,
    salaryMin,
    salaryMax,
    responsibilities,
    requirements,
    tags,
    publishDate,
  } = req.body || {};
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    const updates = [];
    const values = [];
    if (name !== undefined) {
      updates.push('name = ?');
      values.push(name);
    }
    if (sortOrder !== undefined) {
      updates.push('sort_order = ?');
      values.push(sortOrder);
    }
    if (updates.length) {
      values.push(id);
      await pool.query(`UPDATE \`position\` SET ${updates.join(', ')} WHERE id = ?`, values);
    }

    // 同步更新内存中的扩展字段
    const prev = positionExtras.get(id) || {};
    const nextExtras = {
      ...prev,
      ...(city !== undefined ? { city } : {}),
      ...(workExperience !== undefined ? { workExperience } : {}),
      ...(education !== undefined ? { education } : {}),
      ...(salaryMin !== undefined ? { salaryMin } : {}),
      ...(salaryMax !== undefined ? { salaryMax } : {}),
      ...(responsibilities !== undefined ? { responsibilities } : {}),
      ...(requirements !== undefined ? { requirements } : {}),
      ...(tags !== undefined ? { tags } : {}),
      ...(publishDate !== undefined ? { publishDate } : {}),
    };
    positionExtras.set(id, nextExtras);

    return res.json(ok(null));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.delete('/api/positions/:id', authMiddleware, adminMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    await pool.query('DELETE FROM `position` WHERE id = ?', [id]);
    return res.json(ok(null));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 题库 -----
app.get('/api/question-bank', authMiddleware, async (req, res) => {
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const pageSize = Math.min(50, Math.max(1, parseInt(req.query.pageSize, 10) || 10));
  const positionId = req.query.positionId ? parseInt(req.query.positionId, 10) : null;
  const offset = (page - 1) * pageSize;
  try {
    let where = '';
    const params = [];
    if (positionId && !isNaN(positionId)) {
      where = 'WHERE q.position_id = ?';
      params.push(positionId);
    }
    const countSql = `SELECT COUNT(*) AS total FROM question_bank q ${where}`;
    const [countRows] = await pool.query(countSql, params);
    const total = countRows[0].total;

    const listParams = [...params, pageSize, offset];
    const [rows] = await pool.query(
      `SELECT q.id, q.position_id AS positionId, p.name AS positionName, q.question, q.answer, q.knowledge_tags AS knowledgeTags
       FROM question_bank q LEFT JOIN \`position\` p ON q.position_id = p.id ${where} ORDER BY q.id DESC LIMIT ? OFFSET ?`,
      listParams
    );
    return res.json(ok({ list: rows, total }));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.get('/api/question-bank/:id', authMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    const [rows] = await pool.query(
      'SELECT q.id, q.position_id AS positionId, p.name AS positionName, q.question, q.answer, q.knowledge_tags AS knowledgeTags FROM question_bank q LEFT JOIN `position` p ON q.position_id = p.id WHERE q.id = ?',
      [id]
    );
    if (rows.length === 0) return res.status(404).json(fail(404, '题目不存在'));
    return res.json(ok(rows[0]));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.post('/api/question-bank', authMiddleware, adminMiddleware, async (req, res) => {
  const { positionId, question, answer, knowledgeTags } = req.body || {};
  if (!positionId || !question) return res.json(fail(400, '岗位和题目必填'));
  try {
    const [r] = await pool.query(
      'INSERT INTO question_bank (position_id, question, answer, knowledge_tags) VALUES (?, ?, ?, ?)',
      [positionId, question, answer || null, knowledgeTags || null]
    );
    return res.json(ok({ id: r.insertId, positionId, question, answer: answer || null, knowledgeTags: knowledgeTags || null }));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.put('/api/question-bank/:id', authMiddleware, adminMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  const { positionId, question, answer, knowledgeTags } = req.body || {};
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    const updates = [];
    const values = [];
    if (positionId !== undefined) {
      updates.push('position_id = ?');
      values.push(positionId);
    }
    if (question !== undefined) {
      updates.push('question = ?');
      values.push(question);
    }
    if (answer !== undefined) {
      updates.push('answer = ?');
      values.push(answer);
    }
    if (knowledgeTags !== undefined) {
      updates.push('knowledge_tags = ?');
      values.push(knowledgeTags);
    }
    if (updates.length === 0) return res.json(ok(null));
    values.push(id);
    await pool.query(`UPDATE question_bank SET ${updates.join(', ')} WHERE id = ?`, values);
    return res.json(ok(null));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.delete('/api/question-bank/:id', authMiddleware, adminMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    await pool.query('DELETE FROM question_bank WHERE id = ?', [id]);
    return res.json(ok(null));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 面试记录 -----
app.post('/api/interview-record', authMiddleware, async (req, res) => {
  const { positionId } = req.body || {};
  const userId = req.user.id;
  if (!positionId) return res.json(fail(400, '岗位必选'));
  const startedAt = new Date().toISOString().slice(0, 19).replace('T', ' ');
  try {
    const [r] = await pool.query(
      'INSERT INTO interview_record (user_id, position_id, started_at) VALUES (?, ?, ?)',
      [userId, positionId, startedAt]
    );
    return res.json(
      ok({
        id: r.insertId,
        userId: Number(userId),
        positionId: Number(positionId),
        startedAt,
      })
    );
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.get('/api/interview-record', authMiddleware, async (req, res) => {
  const userId = req.user.id;
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const pageSize = Math.min(50, Math.max(1, parseInt(req.query.pageSize, 10) || 10));
  const offset = (page - 1) * pageSize;
  try {
    const [countRows] = await pool.query('SELECT COUNT(*) AS total FROM interview_record WHERE user_id = ?', [userId]);
    const total = countRows[0].total;
    const [rows] = await pool.query(
      `SELECT r.id, r.position_id AS positionId, p.name AS positionName, r.started_at AS startedAt, r.ended_at AS endedAt, r.total_score AS totalScore
       FROM interview_record r LEFT JOIN \`position\` p ON r.position_id = p.id WHERE r.user_id = ? ORDER BY r.started_at DESC LIMIT ? OFFSET ?`,
      [userId, pageSize, offset]
    );
    return res.json(ok({ list: rows, total }));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.get('/api/interview-record/:id', authMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  const userId = req.user.id;
  const isAdmin = req.user.roleId === 2;
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    const [rows] = await pool.query(
      `SELECT r.id, r.user_id AS userId, r.position_id AS positionId, p.name AS positionName, r.started_at AS startedAt, r.ended_at AS endedAt, r.total_score AS totalScore
       FROM interview_record r LEFT JOIN \`position\` p ON r.position_id = p.id WHERE r.id = ?`,
      [id]
    );
    if (rows.length === 0) return res.status(404).json(fail(404, '记录不存在'));
    const row = rows[0];
    if (Number(row.userId) !== Number(userId) && !isAdmin) {
      return res.status(403).json(fail(403, '无权限'));
    }
    const [details] = await pool.query(
      'SELECT id, interview_record_id AS interviewRecordId, round_index AS roundIndex, role, content, emotion_data AS emotionData, score FROM interview_detail WHERE interview_record_id = ? ORDER BY round_index',
      [id]
    );
    return res.json(ok({ ...row, details }));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.patch('/api/interview-record/:id/end', authMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  const userId = req.user.id;
  const { endedAt, totalScore } = req.body || {};
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    const [rows] = await pool.query('SELECT user_id FROM interview_record WHERE id = ?', [id]);
    if (rows.length === 0) return res.status(404).json(fail(404, '记录不存在'));
    if (Number(rows[0].user_id) !== Number(userId)) {
      return res.status(403).json(fail(403, '无权限'));
    }
    const endTime = endedAt || new Date().toISOString().slice(0, 19).replace('T', ' ');
    const updates = ['ended_at = ?'];
    const values = [endTime];
    if (totalScore !== undefined && totalScore !== null) {
      updates.push('total_score = ?');
      values.push(totalScore);
    }
    values.push(id);
    await pool.query(`UPDATE interview_record SET ${updates.join(', ')} WHERE id = ?`, values);
    return res.json(ok(null));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 面试对话详情 -----
app.post('/api/interview-detail', authMiddleware, async (req, res) => {
  const { interviewRecordId, roundIndex, role, content, emotionData, score } = req.body || {};
  const userId = req.user.id;
  if (!interviewRecordId || roundIndex === undefined || !role || !content) {
    return res.json(fail(400, 'interviewRecordId、roundIndex、role、content 必填'));
  }
  try {
    const [rows] = await pool.query('SELECT user_id FROM interview_record WHERE id = ?', [interviewRecordId]);
    if (rows.length === 0) return res.status(404).json(fail(404, '面试记录不存在'));
    if (Number(rows[0].user_id) !== Number(userId)) {
      return res.status(403).json(fail(403, '无权限'));
    }
    const emotionJson = emotionData ? JSON.stringify(emotionData) : null;
    const [r] = await pool.query(
      'INSERT INTO interview_detail (interview_record_id, round_index, role, content, emotion_data, score) VALUES (?, ?, ?, ?, ?, ?)',
      [interviewRecordId, roundIndex, role, content, emotionJson, score ?? null]
    );
    return res.json(
      ok({
        id: r.insertId,
        interviewRecordId,
        roundIndex,
        role,
        content,
        emotionData: emotionData || null,
        score: score ?? null,
      })
    );
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 报告 -----
app.get('/api/report', authMiddleware, async (req, res) => {
  const interviewRecordId = parseInt(req.query.interviewRecordId, 10);
  const userId = req.user.id;
  const isAdmin = req.user.roleId === 2;
  if (!interviewRecordId || isNaN(interviewRecordId)) {
    return res.json(fail(400, 'interviewRecordId 必填'));
  }
  try {
    const [rows] = await pool.query(
      'SELECT rep.id, rep.interview_record_id AS interviewRecordId, rep.content FROM report rep JOIN interview_record r ON rep.interview_record_id = r.id WHERE rep.interview_record_id = ?',
      [interviewRecordId]
    );
    if (rows.length === 0) return res.status(404).json(fail(404, '报告不存在'));
    const row = rows[0];
    const [rec] = await pool.query('SELECT user_id FROM interview_record WHERE id = ?', [interviewRecordId]);
    if (rec.length === 0) return res.status(404).json(fail(404, '记录不存在'));
    if (Number(rec[0].user_id) !== Number(userId) && !isAdmin) {
      return res.status(403).json(fail(403, '无权限'));
    }
    return res.json(ok(row));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.post('/api/report', authMiddleware, async (req, res) => {
  const { interviewRecordId, content } = req.body || {};
  if (!interviewRecordId || content === undefined) return res.json(fail(400, 'interviewRecordId 和 content 必填'));
  try {
    const contentStr = typeof content === 'string' ? content : JSON.stringify(content);
    await pool.query(
      'INSERT INTO report (interview_record_id, content) VALUES (?, ?) ON DUPLICATE KEY UPDATE content = VALUES(content), updated_at = CURRENT_TIMESTAMP',
      [interviewRecordId, contentStr]
    );
    return res.json(ok(null));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 热门岗位（招聘信息，首页展示 & 搜索，使用 job 表） -----
// 将数据库中的公司名称映射为前端使用的 logo 标识（如 ByteDance / Alibaba 等）
function withCompanyLogo(row) {
  const logoMap = {
    '字节跳动': 'ByteDance',
    '阿里巴巴': 'Alibaba',
    '腾讯': 'Tencent',
    '美团': 'Meituan',
    '华为': 'Huawei',
    '网易': 'NetEase',
    '滴滴': 'Didi',
    '小米': 'Xiaomi',
  };
  const logo = row.companyLogo || logoMap[row.companyName] || null;
  return { ...row, companyLogo: logo };
}

app.get('/api/jobs/hot', authMiddleware, async (req, res) => {
  const limit = Math.min(20, Math.max(1, parseInt(req.query.limit, 10) || 10));
  try {
    const [rawRows] = await pool.query(
      'SELECT id, name, company_name AS companyName, company_logo AS companyLogo, salary_min AS salaryMin, salary_max AS salaryMax, job_content AS jobContent, type FROM job ORDER BY id DESC LIMIT ?',
      [limit]
    );
    const rows = rawRows.map(withCompanyLogo);
    return res.json(ok(rows));
  } catch (err) {
    console.error('获取热门岗位失败:', err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// 招聘岗位搜索（关键词 + 岗位类型筛选）
// 注意：必须放在 /api/jobs/:id 之前注册，否则会被当作 :id 路径处理
app.get('/api/jobs/search', authMiddleware, async (req, res) => {
  const keywordRaw = (req.query.keyword || '').toString().trim();
  const type = (req.query.type || '').toString().trim();
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const pageSize = Math.min(50, Math.max(1, parseInt(req.query.pageSize, 10) || 8));
  const offset = (page - 1) * pageSize;

  const keyword = keywordRaw.toLowerCase();

  try {
    let where = '1=1';
    const params = [];

    if (keyword) {
      where += ' AND (LOWER(name) LIKE ? OR LOWER(company_name) LIKE ? OR LOWER(job_content) LIKE ?)';
      const kw = `%${keyword}%`;
      params.push(kw, kw, kw);
    }
    if (type) {
      where += ' AND type = ?';
      params.push(type);
    }

    const [countRows] = await pool.query(
      `SELECT COUNT(*) AS total FROM job WHERE ${where}`,
      params
    );
    const total = countRows[0].total || 0;

    const listParams = [...params, pageSize, offset];
    const [rawRows] = await pool.query(
      `SELECT id, name, company_name AS companyName, company_logo AS companyLogo, salary_min AS salaryMin, salary_max AS salaryMax, job_content AS jobContent, type
       FROM job
       WHERE ${where}
       ORDER BY id DESC
       LIMIT ? OFFSET ?`,
      listParams
    );

    const rows = rawRows.map(withCompanyLogo);
    return res.json(ok({ list: rows, total }));
  } catch (err) {
    console.error('搜索岗位失败:', err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.get('/api/jobs/:id', authMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    const [rawRows] = await pool.query(
      'SELECT id, name, company_name AS companyName, company_logo AS companyLogo, salary_min AS salaryMin, salary_max AS salaryMax, job_content AS jobContent, type FROM job WHERE id = ?',
      [id]
    );
    if (rawRows.length === 0) return res.status(404).json(fail(404, '岗位不存在'));
    return res.json(ok(withCompanyLogo(rawRows[0])));
  } catch (err) {
    console.error('获取岗位详情失败:', err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 学习资源 -----
app.get('/api/learning-resource', authMiddleware, async (req, res) => {
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const pageSize = Math.min(50, Math.max(1, parseInt(req.query.pageSize, 10) || 10));
  const tags = req.query.tags ? String(req.query.tags).trim() : null;
  const offset = (page - 1) * pageSize;
  try {
    let where = '';
    const params = [];
    if (tags) {
      const tagList = tags.split(',').map((t) => t.trim()).filter(Boolean);
      if (tagList.length) {
        where = 'WHERE ' + tagList.map(() => 'tags LIKE ?').join(' OR ');
        tagList.forEach((t) => params.push('%' + t + '%'));
      }
    }
    const countSql = `SELECT COUNT(*) AS total FROM learning_resource ${where}`;
    const [countRows] = await pool.query(countSql, params);
    const total = countRows[0].total;
    const listParams = [...params, pageSize, offset];
    const [rows] = await pool.query(
      `SELECT id, title, link, tags FROM learning_resource ${where} ORDER BY id DESC LIMIT ? OFFSET ?`,
      listParams
    );
    return res.json(ok({ list: rows, total }));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.post('/api/learning-resource', authMiddleware, adminMiddleware, async (req, res) => {
  const { title, link, tags } = req.body || {};
  if (!title || !link) return res.json(fail(400, '标题和链接必填'));
  try {
    const [r] = await pool.query('INSERT INTO learning_resource (title, link, tags) VALUES (?, ?, ?)', [
      title,
      link,
      tags || null,
    ]);
    return res.json(ok({ id: r.insertId, title, link, tags: tags || null }));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.put('/api/learning-resource/:id', authMiddleware, adminMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  const { title, link, tags } = req.body || {};
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    const updates = [];
    const values = [];
    if (title !== undefined) {
      updates.push('title = ?');
      values.push(title);
    }
    if (link !== undefined) {
      updates.push('link = ?');
      values.push(link);
    }
    if (tags !== undefined) {
      updates.push('tags = ?');
      values.push(tags);
    }
    if (updates.length === 0) return res.json(ok(null));
    values.push(id);
    await pool.query(`UPDATE learning_resource SET ${updates.join(', ')} WHERE id = ?`, values);
    return res.json(ok(null));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.delete('/api/learning-resource/:id', authMiddleware, adminMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    await pool.query('DELETE FROM learning_resource WHERE id = ?', [id]);
    return res.json(ok(null));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 用户列表（管理员） -----
app.get('/api/users', authMiddleware, adminMiddleware, async (req, res) => {
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const pageSize = Math.min(50, Math.max(1, parseInt(req.query.pageSize, 10) || 10));
  const offset = (page - 1) * pageSize;
  try {
    const [countRows] = await pool.query('SELECT COUNT(*) AS total FROM `user`');
    const total = countRows[0].total;
    const [rows] = await pool.query(
      'SELECT u.id, u.username, u.email, u.avatar_url AS avatar, u.role_id AS roleId, r.name AS roleName FROM `user` u JOIN role r ON u.role_id = r.id ORDER BY u.id LIMIT ? OFFSET ?',
      [pageSize, offset]
    );
    const list = rows.map((u) => ({
      id: Number(u.id),
      username: u.username,
      email: u.email || undefined,
      avatar: u.avatar || undefined,
      roleId: u.roleId,
      roleName: u.roleName,
    }));
    return res.json(ok({ list, total }));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.get('/api/users/:id', authMiddleware, adminMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    const [rows] = await pool.query(
      'SELECT id, username, email, role_id AS roleId, avatar_url AS avatar FROM `user` WHERE id = ?',
      [id]
    );
    if (rows.length === 0) return res.json(fail(1005, '用户不存在'));
    const user = rows[0];
    return res.json(
      ok({
        id: Number(user.id),
        username: user.username,
        email: user.email || undefined,
        roleId: Number(user.roleId),
        avatar: user.avatar || undefined,
      })
    );
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.post('/api/users', authMiddleware, adminMiddleware, async (req, res) => {
  const { username, password, email, roleId } = req.body || {};
  if (!String(username || '').trim() || !String(password || '').trim()) {
    return res.json(fail(1001, '用户名或密码不能为空'));
  }
  const safeRoleId = Number(roleId) === 2 ? 2 : 1;
  try {
    const [exists] = await pool.query('SELECT id FROM `user` WHERE username = ?', [String(username).trim()]);
    if (exists.length > 0) {
      return res.json(fail(1003, '用户名已存在'));
    }
    await pool.query('INSERT INTO `user` (username, password, email, role_id) VALUES (?, ?, ?, ?)', [
      String(username).trim(),
      String(password),
      email ? String(email).trim() : null,
      safeRoleId,
    ]);
    return res.json(ok(null, '创建用户成功'));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.put('/api/users/:id', authMiddleware, adminMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));

  const { username, email, roleId, password } = req.body || {};
  try {
    const [rows] = await pool.query('SELECT id FROM `user` WHERE id = ?', [id]);
    if (rows.length === 0) return res.json(fail(1005, '用户不存在'));

    if (username !== undefined) {
      const name = String(username).trim();
      if (!name) return res.json(fail(1001, '用户名不能为空'));
      const [sameNameRows] = await pool.query('SELECT id FROM `user` WHERE username = ? AND id <> ?', [name, id]);
      if (sameNameRows.length > 0) {
        return res.json(fail(1003, '用户名已存在'));
      }
    }

    const updates = [];
    const values = [];
    if (username !== undefined) {
      updates.push('username = ?');
      values.push(String(username).trim());
    }
    if (email !== undefined) {
      updates.push('email = ?');
      values.push(email ? String(email).trim() : null);
    }
    if (roleId !== undefined) {
      updates.push('role_id = ?');
      values.push(Number(roleId) === 2 ? 2 : 1);
    }
    if (password !== undefined) {
      updates.push('password = ?');
      values.push(String(password));
    }
    if (updates.length === 0) return res.json(ok(null, '更新用户成功'));

    values.push(id);
    await pool.query(`UPDATE \`user\` SET ${updates.join(', ')} WHERE id = ?`, values);
    return res.json(ok(null, '更新用户成功'));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

app.delete('/api/users/:id', authMiddleware, adminMiddleware, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) return res.status(400).json(fail(400, '无效 ID'));
  try {
    const [rows] = await pool.query('SELECT id FROM `user` WHERE id = ?', [id]);
    if (rows.length === 0) return res.json(fail(1005, '用户不存在'));
    if (Number(req.user.id) === id) {
      return res.status(400).json(fail(400, '不允许删除当前登录管理员'));
    }
    await pool.query('DELETE FROM `user` WHERE id = ?', [id]);
    return res.json(ok(null, '删除用户成功'));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 后台管理：全部面试记录（仅管理员） -----
app.get('/api/admin/interview-record', authMiddleware, adminMiddleware, async (req, res) => {
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const pageSize = Math.min(50, Math.max(1, parseInt(req.query.pageSize, 10) || 10));
  const userId = req.query.userId ? parseInt(req.query.userId, 10) : null;
  const positionId = req.query.positionId ? parseInt(req.query.positionId, 10) : null;
  const offset = (page - 1) * pageSize;
  try {
    let where = '1=1';
    const params = [];
    if (userId && !isNaN(userId)) {
      where += ' AND r.user_id = ?';
      params.push(userId);
    }
    if (positionId && !isNaN(positionId)) {
      where += ' AND r.position_id = ?';
      params.push(positionId);
    }
    const [countRows] = await pool.query(
      `SELECT COUNT(*) AS total FROM interview_record r WHERE ${where}`,
      params
    );
    const total = countRows[0].total;
    const listParams = [...params, pageSize, offset];
    const [rows] = await pool.query(
      `SELECT r.id, r.user_id AS userId, u.username AS userName, r.position_id AS positionId, p.name AS positionName,
       r.started_at AS startedAt, r.ended_at AS endedAt, r.total_score AS totalScore
       FROM interview_record r
       LEFT JOIN \`user\` u ON r.user_id = u.id
       LEFT JOIN \`position\` p ON r.position_id = p.id
       WHERE ${where}
       ORDER BY r.started_at DESC
       LIMIT ? OFFSET ?`,
      listParams
    );
    return res.json(ok({ list: rows, total }));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 后台管理：导出面试记录（仅管理员，返回 JSON） -----
app.get('/api/admin/export/interview-record', authMiddleware, adminMiddleware, async (req, res) => {
  const userId = req.query.userId ? parseInt(req.query.userId, 10) : null;
  const positionId = req.query.positionId ? parseInt(req.query.positionId, 10) : null;
  const limit = Math.min(1000, Math.max(1, parseInt(req.query.limit, 10) || 500));
  try {
    let where = '1=1';
    const params = [];
    if (userId && !isNaN(userId)) {
      where += ' AND r.user_id = ?';
      params.push(userId);
    }
    if (positionId && !isNaN(positionId)) {
      where += ' AND r.position_id = ?';
      params.push(positionId);
    }
    params.push(limit);
    const [rows] = await pool.query(
      `SELECT r.id, r.user_id AS userId, u.username AS userName, r.position_id AS positionId, p.name AS positionName,
       r.started_at AS startedAt, r.ended_at AS endedAt, r.total_score AS totalScore
       FROM interview_record r
       LEFT JOIN \`user\` u ON r.user_id = u.id
       LEFT JOIN \`position\` p ON r.position_id = p.id
       WHERE ${where}
       ORDER BY r.started_at DESC
       LIMIT ?`,
      params
    );
    const accept = req.headers.accept || '';
    if (accept.includes('application/json')) {
      return res.json(ok(rows));
    }
    res.setHeader('Content-Disposition', 'attachment; filename=interview-records.json');
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    return res.send(JSON.stringify(rows, null, 2));
  } catch (err) {
    console.error(err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// ----- 模拟面试 AI（豆包流式 / 本地回退） -----
// 上传面试用简历（PDF/Word）
app.post('/api/interview-ai/resume', authMiddleware, uploadInterviewResume.single('file'), (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json(fail(400, '请选择要上传的文件'));
    }
    return res.json(
      ok({
        originalName: req.file.originalname,
        storedName: req.file.filename,
        size: req.file.size,
      })
    );
  } catch (err) {
    console.error('面试简历上传失败:', err);
    return res.status(500).json(fail(500, '服务器错误'));
  }
});

// 创建面试会话：写入 system 提示与候选人填写的岗位/薪资/公司/工作内容等
app.post('/api/interview-ai/session', authMiddleware, async (req, res) => {
  const userId = String(req.user.id);
  const {
    jobId,
    positionName,
    salaryExpected,
    companyName,
    jobContent,
    interviewMode,
    aiAvatar,
    resumeStoredName,
    resumeOriginalName,
  } = req.body || {};

  if (!positionName || !String(positionName).trim()) {
    return res.json(fail(400, '请填写面试岗位'));
  }
  const mode = interviewMode === 'voice' ? 'voice' : 'text';
  const avatar = aiAvatar ? String(aiAvatar) : 'girl-a';

  const sessionId = crypto.randomUUID();
  const systemContent = buildInterviewSystemPrompt({
    positionName: String(positionName).trim(),
    salaryExpected: salaryExpected != null ? String(salaryExpected) : '',
    companyName: companyName != null ? String(companyName) : '',
    jobContent: jobContent != null ? String(jobContent) : '',
    interviewMode: mode,
    resumeOriginalName: resumeOriginalName || null,
  });

  let interviewRecordId = null;
  try {
    if (jobId != null && Number(jobId) > 0) {
      const startedAt = new Date().toISOString().slice(0, 19).replace('T', ' ');
      const [r] = await pool.query(
        'INSERT INTO interview_record (user_id, position_id, started_at) VALUES (?, ?, ?)',
        [Number(userId), Number(jobId), startedAt]
      );
      interviewRecordId = r.insertId;
    }
  } catch (e) {
    console.error('创建 interview_record 失败（继续会话）:', e);
  }

  // 仅创建会话上下文，不在此处调用大模型；首问由前端进入会话页后请求 /interview-ai/opening-stream
  interviewAiSessions.set(sessionId, {
    userId,
    jobId: jobId != null ? Number(jobId) : null,
    interviewMode: mode,
    aiAvatar: avatar,
    resumeStoredName: resumeStoredName || null,
    positionName: String(positionName).trim(),
    interviewRecordId,
    roundCount: 0,
    scoreHistory: [],
    scoreCommentHistory: [],
    finished: false,
    messages: [{ role: 'system', content: systemContent }],
    updatedAt: Date.now(),
  });

  return res.json(
    ok({
      sessionId,
      interviewMode: mode,
      aiAvatar: avatar,
      interviewRecordId,
    })
  );
});

// 进入会话页后调用：生成 AI 首问（豆包）；已存在 assistant 则幂等返回，避免重复扣费
app.post('/api/interview-ai/opening', authMiddleware, async (req, res) => {
  const userId = String(req.user.id);
  const { sessionId } = req.body || {};
  if (!sessionId) return res.json(fail(400, 'sessionId 必填'));

  const session = interviewAiSessions.get(sessionId);
  if (!session || session.userId !== userId) {
    return res.status(404).json(fail(404, '会话不存在或无权访问'));
  }

  const existing = (session.messages || []).find((m) => m.role === 'assistant');
  if (existing && existing.content) {
    return res.json(ok({ openingQuestion: existing.content }));
  }

  const systemMsg = (session.messages || []).find((m) => m.role === 'system');
  const systemContent = systemMsg?.content || '';
  const openingQuestion = await generateOpeningQuestion({
    systemContent,
    positionName: session.positionName || '',
    mode: session.interviewMode,
  });

  session.messages.push({ role: 'assistant', content: openingQuestion });
  session.updatedAt = Date.now();

  return res.json(ok({ openingQuestion }));
});

// 进入会话页后调用：流式生成/恢复 AI 首问（展示效果与常规回答一致）
app.post('/api/interview-ai/opening-stream', authMiddleware, async (req, res) => {
  const userId = String(req.user.id);
  const { sessionId } = req.body || {};
  if (!sessionId) return res.status(400).json(fail(400, 'sessionId 必填'));

  const session = interviewAiSessions.get(sessionId);
  if (!session || session.userId !== userId) {
    return res.status(404).json(fail(404, '会话不存在或无权访问'));
  }

  res.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');
  if (res.flushHeaders) res.flushHeaders();

  const sendError = (msg) => {
    res.write(`data: ${JSON.stringify({ error: msg })}\n\n`);
    res.write('data: [DONE]\n\n');
    res.end();
  };

  try {
    const existing = (session.messages || []).find((m) => m.role === 'assistant');
    if (existing && existing.content) {
      await writeMockStream(res, existing.content);
      res.write('data: [DONE]\n\n');
      res.end();
      return;
    }

    const systemMsg = (session.messages || []).find((m) => m.role === 'system');
    const systemContent = systemMsg?.content || '';

    if (session.interviewMode === 'voice') {
      const tip =
        '欢迎来到语音面试（占位模式）。当前版本先不做语音识别与情感分析，您可以先切换文本模式体验。';
      await writeMockStream(res, tip);
      session.messages.push({ role: 'assistant', content: tip });
      session.updatedAt = Date.now();
      res.write('data: [DONE]\n\n');
      res.end();
      return;
    }

    const fallback =
      `你好，我是本次面试官。我们先从自我介绍开始：请你用 1-2 分钟介绍一下你与「${session.positionName || '目标岗位'}」最相关的项目经历与技术亮点。`;

    if (ARK_API_KEY && ARK_ENDPOINT_ID) {
      const upstream = await fetch(ARK_CHAT_COMPLETIONS_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${ARK_API_KEY}`,
        },
        body: JSON.stringify({
          model: ARK_ENDPOINT_ID,
          stream: true,
          messages: [
            { role: 'system', content: systemContent },
            {
              role: 'user',
              content:
                '请你作为面试官先手发起第一问。要求：1）只输出一段自然中文提问；2）不超过120字；3）紧贴候选人目标岗位；4）不要输出前缀标题。',
            },
          ],
        }),
      });

      if (!upstream.ok) {
        const errText = await upstream.text().catch(() => upstream.statusText);
        console.error('opening-stream 豆包 API 错误:', upstream.status, errText);
        await writeMockStream(res, fallback);
        session.messages.push({ role: 'assistant', content: fallback });
        session.updatedAt = Date.now();
        res.write('data: [DONE]\n\n');
        res.end();
        return;
      }

      let fullAssistant = '';
      const reader = upstream.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const parts = buf.split('\n\n');
        buf = parts.pop() || '';
        for (const block of parts) {
          const line = block.trim().split('\n').find((l) => l.startsWith('data:'));
          if (!line) continue;
          const dataStr = line.replace(/^data:\s*/, '').trim();
          if (dataStr === '[DONE]') {
            const finalText = fullAssistant || fallback;
            session.messages.push({ role: 'assistant', content: finalText });
            session.updatedAt = Date.now();
            res.write('data: [DONE]\n\n');
            res.end();
            return;
          }
          try {
            const json = JSON.parse(dataStr);
            const piece =
              json.choices &&
              json.choices[0] &&
              json.choices[0].delta &&
              json.choices[0].delta.content;
            if (piece) {
              fullAssistant += piece;
              res.write(`data: ${JSON.stringify({ content: piece })}\n\n`);
            }
          } catch (_) {
            /* ignore */
          }
        }
      }

      const finalText = fullAssistant || fallback;
      if (!fullAssistant) {
        await writeMockStream(res, finalText);
      }
      session.messages.push({ role: 'assistant', content: finalText });
      session.updatedAt = Date.now();
      res.write('data: [DONE]\n\n');
      res.end();
      return;
    }

    await writeMockStream(res, fallback);
    session.messages.push({ role: 'assistant', content: fallback });
    session.updatedAt = Date.now();
    res.write('data: [DONE]\n\n');
    res.end();
  } catch (e) {
    console.error('opening-stream 异常:', e);
    sendError(e.message || '流式输出失败');
  }
});

// 获取会话信息：用于前端刷新后恢复首问、模式和头像
app.get('/api/interview-ai/session/:sessionId', authMiddleware, (req, res) => {
  const userId = String(req.user.id);
  const { sessionId } = req.params;
  const session = interviewAiSessions.get(sessionId);
  if (!session || session.userId !== userId) {
    return res.status(404).json(fail(404, '会话不存在或无权访问'));
  }
  const openingQuestion =
    (session.messages || []).find((m) => m.role === 'assistant')?.content || '';
  return res.json(
    ok({
      sessionId,
      interviewMode: session.interviewMode,
      aiAvatar: session.aiAvatar || 'girl-a',
      openingQuestion,
      interviewRecordId: session.interviewRecordId || null,
      finished: !!session.finished,
    })
  );
});

// 流式对话：SSE，每行 data: {"content":"..."} ，结束 data: [DONE]
app.post('/api/interview-ai/chat-stream', authMiddleware, async (req, res) => {
  const userId = String(req.user.id);
  const { sessionId, message } = req.body || {};
  if (!sessionId || !message || !String(message).trim()) {
    return res.status(400).json(fail(400, 'sessionId 与 message 必填'));
  }

  const session = interviewAiSessions.get(sessionId);
  if (!session || session.userId !== userId) {
    return res.status(404).json(fail(404, '会话不存在或无权访问'));
  }

  const userText = String(message).trim();
  if (session.finished) {
    return res.status(400).json(fail(400, '本次面试已结束，请查看报告'));
  }

  const lastAssistant = [...(session.messages || [])].reverse().find((m) => m.role === 'assistant');
  const systemMsg = (session.messages || []).find((m) => m.role === 'system');
  const systemContent = systemMsg?.content || '';

  session.messages.push({ role: 'user', content: userText });
  session.updatedAt = Date.now();

  res.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');
  if (res.flushHeaders) res.flushHeaders();

  const sendError = (msg) => {
    res.write(`data: ${JSON.stringify({ error: msg })}\n\n`);
    res.write('data: [DONE]\n\n');
    res.end();
  };

  try {
    const scoreResult = await scoreInterviewAnswer({
      systemContent,
      question: lastAssistant?.content || '开场问题',
      answer: userText,
    });
    const rawScore = Number(scoreResult.score);
    const scoreComment = scoreResult.comment ? String(scoreResult.comment) : '';
    session.roundCount = Number(session.roundCount || 0) + 1;
    session.scoreHistory = Array.isArray(session.scoreHistory) ? session.scoreHistory : [];
    session.scoreCommentHistory = Array.isArray(session.scoreCommentHistory) ? session.scoreCommentHistory : [];
    session.scoreHistory.push(rawScore);
    if (scoreComment) session.scoreCommentHistory.push(scoreComment);

    if (session.interviewRecordId) {
      try {
        await pool.query(
          'INSERT INTO interview_detail (interview_record_id, round_index, role, content, emotion_data, score) VALUES (?, ?, ?, ?, ?, ?)',
          [session.interviewRecordId, session.roundCount * 2 - 1, 'candidate', userText, null, rawScore]
        );
      } catch (e) {
        console.error('保存候选人回答明细失败:', e);
      }
    }

    const shouldFinish =
      rawScore > AI_INTERVIEW_SCORE_MAX ||
      rawScore < AI_INTERVIEW_SCORE_MIN ||
      session.roundCount >= AI_INTERVIEW_MAX_QUESTIONS;

    if (shouldFinish) {
      const validScores = (session.scoreHistory || []).filter((s) => typeof s === 'number' && !Number.isNaN(s));
      const avgScore = validScores.length
        ? validScores.reduce((a, b) => a + b, 0) / validScores.length
        : 0;
      const reportContent = await buildInterviewReportContent({
        positionName: session.positionName || '',
        rounds: session.roundCount,
        avgScore,
        scoreComments: session.scoreCommentHistory || [],
      });

      if (session.interviewRecordId) {
        try {
          const contentStr = JSON.stringify(reportContent);
          await pool.query(
            'INSERT INTO report (interview_record_id, content) VALUES (?, ?) ON DUPLICATE KEY UPDATE content = VALUES(content), updated_at = CURRENT_TIMESTAMP',
            [session.interviewRecordId, contentStr]
          );
          const endedAt = new Date().toISOString().slice(0, 19).replace('T', ' ');
          await pool.query('UPDATE interview_record SET ended_at = ?, total_score = ? WHERE id = ?', [
            endedAt,
            reportContent.totalScore ?? Math.max(0, Math.min(10, Number(avgScore.toFixed(1)))),
            session.interviewRecordId,
          ]);
        } catch (e) {
          console.error('保存面试报告失败:', e);
        }
      }

      session.finished = true;
      const endText =
        `本轮回答评分：${rawScore}/10。${scoreComment ? `点评：${scoreComment}` : ''}\n` +
        `本次面试已结束。点击查看本次面试报告。`;
      await writeMockStream(res, endText);
      session.messages.push({ role: 'assistant', content: endText });
      if (session.interviewRecordId) {
        try {
          await pool.query(
            'INSERT INTO interview_detail (interview_record_id, round_index, role, content, emotion_data, score) VALUES (?, ?, ?, ?, ?, ?)',
            [session.interviewRecordId, session.roundCount * 2, 'interviewer', endText, null, null]
          );
        } catch (e) {
          console.error('保存面试官结束语失败:', e);
        }
      }
      res.write(
        `data: ${JSON.stringify({
          event: 'interview_end',
          interviewRecordId: session.interviewRecordId || null,
          score: rawScore,
        })}\n\n`
      );
      res.write('data: [DONE]\n\n');
      res.end();
      return;
    }

    const scorePrefix = `本轮回答评分：${rawScore}/10。${scoreComment ? `点评：${scoreComment}` : ''}\n`;
    await writeMockStream(res, scorePrefix);

    // 语音模式：仅占位——仍返回一段说明性文字（整段流式输出）
    if (session.interviewMode === 'voice') {
      const tip =
        '【语音面试模式占位】当前版本尚未接入语音识别与情感分析。后续将支持：语音输入 → 情感判断 → AI 生成完整回复供数字人播报。请先切换到「文本面试」体验流式对话，或等待后续迭代。';
      const finalTip = scorePrefix + tip;
      await writeMockStream(res, tip);
      session.messages.push({ role: 'assistant', content: finalTip });
      if (session.interviewRecordId) {
        try {
          await pool.query(
            'INSERT INTO interview_detail (interview_record_id, round_index, role, content, emotion_data, score) VALUES (?, ?, ?, ?, ?, ?)',
            [session.interviewRecordId, session.roundCount * 2, 'interviewer', finalTip, null, null]
          );
        } catch (e) {
          console.error('保存语音占位回复失败:', e);
        }
      }
      res.write('data: [DONE]\n\n');
      res.end();
      return;
    }

    const arkMessages = session.messages.map((m) => ({
      role: m.role === 'assistant' ? 'assistant' : m.role === 'user' ? 'user' : 'system',
      content: m.content,
    }));

    if (ARK_API_KEY && ARK_ENDPOINT_ID) {
      const upstream = await fetch(ARK_CHAT_COMPLETIONS_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${ARK_API_KEY}`,
        },
        body: JSON.stringify({
          model: ARK_ENDPOINT_ID,
          messages: arkMessages,
          stream: true,
        }),
      });

      if (!upstream.ok) {
        const errText = await upstream.text().catch(() => upstream.statusText);
        console.error('豆包 API 错误:', upstream.status, errText);
        let assistantFallback =
          '（豆包接口调用失败，已切换本地模拟回复）请简单介绍一下你与「' +
          (session.messages[0] && session.messages[0].content.slice(0, 80)) +
          '」相关的项目经验。';
        await writeMockStream(res, assistantFallback);
        const finalFallback = scorePrefix + assistantFallback;
        session.messages.push({ role: 'assistant', content: finalFallback });
        if (session.interviewRecordId) {
          try {
            await pool.query(
              'INSERT INTO interview_detail (interview_record_id, round_index, role, content, emotion_data, score) VALUES (?, ?, ?, ?, ?, ?)',
              [session.interviewRecordId, session.roundCount * 2, 'interviewer', finalFallback, null, null]
            );
          } catch (e) {
            console.error('保存面试官回退回复失败:', e);
          }
        }
        res.write('data: [DONE]\n\n');
        res.end();
        return;
      }

      let fullAssistant = scorePrefix;
      const reader = upstream.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const parts = buf.split('\n\n');
        buf = parts.pop() || '';
        for (const block of parts) {
          const line = block.trim().split('\n').find((l) => l.startsWith('data:'));
          if (!line) continue;
          const dataStr = line.replace(/^data:\s*/, '').trim();
          if (dataStr === '[DONE]') {
            const finalAssistant = fullAssistant || scorePrefix + '（无回复内容）';
            session.messages.push({ role: 'assistant', content: finalAssistant });
            if (session.interviewRecordId) {
              try {
                await pool.query(
                  'INSERT INTO interview_detail (interview_record_id, round_index, role, content, emotion_data, score) VALUES (?, ?, ?, ?, ?, ?)',
                  [session.interviewRecordId, session.roundCount * 2, 'interviewer', finalAssistant, null, null]
                );
              } catch (e) {
                console.error('保存面试官回复失败:', e);
              }
            }
            res.write('data: [DONE]\n\n');
            res.end();
            return;
          }
          try {
            const json = JSON.parse(dataStr);
            const piece =
              json.choices &&
              json.choices[0] &&
              json.choices[0].delta &&
              json.choices[0].delta.content;
            if (piece) {
              fullAssistant += piece;
              res.write(`data: ${JSON.stringify({ content: piece })}\n\n`);
            }
          } catch (_) {
            /* ignore */
          }
        }
      }
      const finalAssistant = fullAssistant || scorePrefix + '（无回复内容）';
      session.messages.push({ role: 'assistant', content: finalAssistant });
      if (session.interviewRecordId) {
        try {
          await pool.query(
            'INSERT INTO interview_detail (interview_record_id, round_index, role, content, emotion_data, score) VALUES (?, ?, ?, ?, ?, ?)',
            [session.interviewRecordId, session.roundCount * 2, 'interviewer', finalAssistant, null, null]
          );
        } catch (e) {
          console.error('保存面试官回复失败:', e);
        }
      }
      res.write('data: [DONE]\n\n');
      res.end();
      return;
    }

    // 未配置密钥：模拟面试官回复
    const mock =
      '感谢您的回答。结合您应聘的岗位，我想进一步了解：在最近一个项目中，您负责的核心模块是什么？遇到了哪些技术难点，又是如何解决的？';
    await writeMockStream(res, mock);
    const finalMock = scorePrefix + mock;
    session.messages.push({ role: 'assistant', content: finalMock });
    if (session.interviewRecordId) {
      try {
        await pool.query(
          'INSERT INTO interview_detail (interview_record_id, round_index, role, content, emotion_data, score) VALUES (?, ?, ?, ?, ?, ?)',
          [session.interviewRecordId, session.roundCount * 2, 'interviewer', finalMock, null, null]
        );
      } catch (e) {
        console.error('保存面试官模拟回复失败:', e);
      }
    }
    res.write('data: [DONE]\n\n');
    res.end();
  } catch (e) {
    console.error('chat-stream 异常:', e);
    sendError(e.message || '流式输出失败');
  }
});

// ----- 新版面试接口（与最新联调文档对齐） -----
app.post('/api/interview/start', authMiddleware, async (req, res) => {
  const userId = String(req.user.id);
  const { resume, position, collection_name, interview_mode } = req.body || {};
  if (!resume || !position || !collection_name) {
    return res.status(400).json({ code: 400, message: 'resume、position、collection_name 必填', data: null });
  }
  const session_id = crypto.randomUUID();
  let topic = inferTopicByText(`${position}\n${resume}`);
  let firstQuestion =
    `请结合你简历中提到的项目经验，谈谈你在应聘「${String(position)}」时，` +
    '遇到过的一个技术挑战，以及你是如何分析并落地解决的？';
  if (ARK_API_KEY && ARK_ENDPOINT_ID) {
    const aiText = await callArkChatOnce([
      {
        role: 'user',
        content:
          `你是技术面试官，请基于候选人信息给出第一道面试题，只输出 JSON：` +
          `{"question":"...","topic":"..."}` +
          `\n岗位：${String(position)}\n题库集合：${String(collection_name)}\n简历：${String(resume).slice(0, 2500)}`,
      },
    ]);
    const obj = extractJsonObject(aiText);
    if (obj && obj.question) {
      firstQuestion = String(obj.question);
      topic = String(obj.topic || topic);
    }
  }
  interviewSessionsV2.set(session_id, {
    userId,
    resume: String(resume),
    position: String(position),
    collection_name: String(collection_name),
    interview_mode: interview_mode === 'avatar' ? 'avatar' : interview_mode === 'voice' ? 'voice' : 'text',
    status: 'questioning',
    total_rounds: 0,
    current_topic: topic,
    current_question: firstQuestion,
    history: [],
  });
  return res.json(
    ok200({
      session_id,
      status: 'questioning',
      total_rounds: 0,
      current_topic: topic,
      current_question: firstQuestion,
      interview_mode: interview_mode === 'avatar' ? 'avatar' : interview_mode === 'voice' ? 'voice' : 'text',
      history: [],
    })
  );
});

app.post('/api/interview/opening-stream', authMiddleware, async (req, res) => {
  const userId = String(req.user.id);
  const { session_id } = req.body || {};
  if (!session_id) {
    return res.status(400).json({ code: 400, message: 'session_id 必填', data: null });
  }
  const session = interviewSessionsV2.get(String(session_id));
  if (!session || session.userId !== userId) {
    return res.status(404).json({ code: 404, message: '会话不存在或无权访问', data: null });
  }

  res.setHeader('Content-Type', 'application/x-ndjson; charset=utf-8');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');

  const writeEvt = (type, data) => {
    res.write(`${JSON.stringify({ type, data, timestamp: new Date().toISOString() })}\n`);
  };

  try {
    writeEvt('analyzing', { message: '正在准备开场问题...' });
    await new Promise((r) => setTimeout(r, 140));

    let topic = session.current_topic || inferTopicByText(`${session.position}\n${session.resume}`);
    let question = session.current_question || '';

    if (!question) {
      question =
        `请结合你简历中提到的项目经验，谈谈你在应聘「${String(session.position)}」时，` +
        '遇到过的一个技术挑战，以及你是如何分析并落地解决的？';
      if (ARK_API_KEY && ARK_ENDPOINT_ID) {
        const aiText = await callArkChatOnce([
          {
            role: 'user',
            content:
              `你是技术面试官，请基于候选人信息给出第一道面试题，只输出 JSON：` +
              `{"question":"...","topic":"..."}` +
              `\n岗位：${String(session.position)}\n题库集合：${String(session.collection_name)}\n简历：${String(session.resume).slice(0, 2500)}`,
          },
        ]);
        const obj = extractJsonObject(aiText);
        if (obj && obj.question) {
          question = String(obj.question);
          topic = String(obj.topic || topic);
        }
      }

      session.current_topic = topic;
      session.current_question = question;
      session.total_rounds = 1;
      session.status = 'questioning';
    }

    for (const ch of String(question)) {
      writeEvt('question_chunk', { chunk: ch });
      // eslint-disable-next-line no-await-in-loop
      await new Promise((r) => setTimeout(r, 10));
    }
    writeEvt('question', {
      answer: question,
      question,
      is_followup: false,
      topic: session.current_topic,
      round: session.total_rounds || 1,
    });
    res.end();
  } catch (e) {
    console.error('/interview/opening-stream 异常:', e);
    writeEvt('error', { message: e.message || '服务器错误' });
    res.end();
  }
});

app.post('/api/interview/answer', authMiddleware, async (req, res) => {
  const userId = String(req.user.id);
  const { session_id, answer } = req.body || {};
  if (!session_id || !answer || !String(answer).trim()) {
    return res.status(400).json({ code: 400, message: 'session_id 与 answer 必填', data: null });
  }
  const session = interviewSessionsV2.get(String(session_id));
  if (!session || session.userId !== userId) {
    return res.status(404).json({ code: 404, message: '会话不存在或无权访问', data: null });
  }
  if (session.status === 'ended') {
    return res.status(400).json({ code: 400, message: '会话已结束', data: null });
  }

  res.setHeader('Content-Type', 'application/x-ndjson; charset=utf-8');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');

  const writeEvt = (type, data) => {
    res.write(`${JSON.stringify({ type, data, timestamp: new Date().toISOString() })}\n`);
  };

  try {
    writeEvt('analyzing', { message: '正在分析回答深度...' });
    await new Promise((r) => setTimeout(r, 150));

    const trimmed = String(answer).trim();
    let depth_score = Math.max(1, Math.min(10, Math.round(Math.min(trimmed.length / 20, 10))));
    let is_vague = depth_score <= 3;
    let need_followup = is_vague || /不知道|不清楚|就这样/.test(trimmed);
    // 先不立即下发，避免后续 AI 覆盖后出现重复 analysis_result 事件
    await new Promise((r) => setTimeout(r, 120));

    const round = Number(session.total_rounds || 1);
    const currentQuestion = session.current_question;
    const currentTopic = session.current_topic;
    session.history.push({
      round,
      question: currentQuestion,
      answer: trimmed,
      topic: currentTopic,
      timestamp: new Date().toISOString(),
    });

    const nextRound = round + 1;
    let nextTopic = inferTopicByText(trimmed);
    let followupMessage = '回答不够深入，准备追问...';
    let followupQuestion = need_followup
      ? `你提到了「${trimmed.slice(0, 20)}...」，请结合一个真实项目案例展开：背景、你做了什么、结果如何？`
      : `你的回答不错。继续追问：在「${session.position}」相关项目里，遇到过最难的稳定性问题是什么，你如何定位并修复？`;

    if (ARK_API_KEY && ARK_ENDPOINT_ID) {
      const aiText = await callArkChatOnce([
        {
          role: 'user',
          content:
            `你是技术面试官，请分析候选人回答并生成下一问，只输出 JSON：` +
            `{"depth_score":1-10,"is_vague":true/false,"need_followup":true/false,"followup_message":"...","topic":"...","question":"..."}` +
            `\n岗位：${session.position}\n题库集合：${session.collection_name}\n当前问题：${currentQuestion}\n候选人回答：${trimmed.slice(0, 3000)}`,
        },
      ]);
      const obj = extractJsonObject(aiText);
      if (obj) {
        if (typeof obj.depth_score === 'number') depth_score = Math.max(1, Math.min(10, Number(obj.depth_score)));
        if (typeof obj.is_vague === 'boolean') is_vague = obj.is_vague;
        if (typeof obj.need_followup === 'boolean') need_followup = obj.need_followup;
        if (obj.topic) nextTopic = String(obj.topic);
        if (obj.question) followupQuestion = String(obj.question);
        if (obj.followup_message) followupMessage = String(obj.followup_message);
        const feedback = need_followup
          ? '感谢你的回答。当前信息还不够具体，请补充一个真实项目里的技术细节与决策过程。'
          : '你的回答较完整，表达清晰。下面我继续追问一个更深入的问题。';
        writeEvt('analysis_result', { depth_score, is_vague, need_followup, feedback });
      }
    }
    if (!(ARK_API_KEY && ARK_ENDPOINT_ID)) {
      const feedback = need_followup
        ? '感谢你的回答。当前信息还不够具体，请补充一个真实项目里的技术细节与决策过程。'
        : '你的回答较完整，表达清晰。下面我继续追问一个更深入的问题。';
      writeEvt('analysis_result', { depth_score, is_vague, need_followup, feedback });
    }

    if (need_followup) {
      writeEvt('followup', { message: followupMessage });
      await new Promise((r) => setTimeout(r, 120));
    }

    if (nextRound > INTERVIEW_MOCK_MAX_ROUNDS) {
      session.status = 'ended';
      session.total_rounds = round;
      writeEvt('interview_complete', {
        session_id: String(session_id),
        message: '面试已结束，可查看评估报告',
      });
      res.end();
      return;
    }

    session.total_rounds = nextRound;
    session.current_topic = nextTopic;
    session.current_question = followupQuestion;
    session.status = 'questioning';

    writeEvt('question', {
      answer: followupQuestion,
      question: followupQuestion,
      is_followup: need_followup,
      topic: nextTopic,
      round: nextRound,
    });
    res.end();
  } catch (e) {
    console.error('新版 /interview/answer 异常:', e);
    writeEvt('error', { message: e.message || '服务器错误' });
    res.end();
  }
});

app.post('/api/interview/answer-voice', authMiddleware, uploadInterviewVoice.single('file'), async (req, res) => {
  const userId = String(req.user.id);
  const { session_id } = req.body || {};
  const voiceFile = req.file;
  if (!session_id) {
    return res.status(400).json({ code: 400, message: 'session_id 必填', data: null });
  }
  if (!voiceFile || !voiceFile.buffer || voiceFile.buffer.length === 0) {
    return res.status(400).json({ code: 400, message: 'file 必填', data: null });
  }
  const session = interviewSessionsV2.get(String(session_id));
  if (!session || session.userId !== userId) {
    return res.status(404).json({ code: 404, message: '会话不存在或无权访问', data: null });
  }
  if (session.status === 'ended') {
    return res.status(400).json({ code: 400, message: '会话已结束', data: null });
  }

  res.setHeader('Content-Type', 'application/x-ndjson; charset=utf-8');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');

  const writeEvt = (type, data) => {
    res.write(`${JSON.stringify({ type, data, timestamp: new Date().toISOString() })}\n`);
  };

  try {
    const approxSecs = Math.max(1, Math.round((voiceFile.size || voiceFile.buffer.length) / 16000));
    const transcript =
      `（模拟转写）我在最近项目中负责核心模块设计与性能优化，` +
      `通过日志与链路追踪定位瓶颈，并完成分阶段改造，最终提升了系统稳定性。`;

    writeEvt('voice_processing', {
      message: '正在录音转写并分析情感...',
      transcript,
      audio_seconds: approxSecs,
      filename: voiceFile.originalname || 'fronten.wav',
    });
    await new Promise((r) => setTimeout(r, 180));

    writeEvt('analyzing', {
      message: '正在分析回答深度（结合情感分析）...',
      transcript,
    });
    await new Promise((r) => setTimeout(r, 150));

    const trimmed = transcript.trim();
    let depth_score = Math.max(1, Math.min(10, Math.round(Math.min(trimmed.length / 24, 10))));
    let is_vague = depth_score <= 3;
    let need_followup = is_vague;

    const round = Number(session.total_rounds || 1);
    const currentQuestion = session.current_question;
    const currentTopic = session.current_topic;
    session.history.push({
      round,
      question: currentQuestion,
      answer: trimmed,
      topic: currentTopic,
      timestamp: new Date().toISOString(),
    });

    const nextRound = round + 1;
    let nextTopic = inferTopicByText(trimmed);
    let followupQuestion =
      `你提到了性能优化，请具体说明：当时最关键的瓶颈指标是什么，` +
      `你如何验证优化真的生效？`;
    let followupMessage = '回答不够深入，准备追问...';

    if (ARK_API_KEY && ARK_ENDPOINT_ID) {
      const aiText = await callArkChatOnce([
        {
          role: 'user',
          content:
            `你是技术面试官，请分析候选人回答并生成下一问，只输出 JSON：` +
            `{"depth_score":1-10,"is_vague":true/false,"need_followup":true/false,"followup_message":"...","topic":"...","question":"..."}` +
            `\n岗位：${session.position}\n题库集合：${session.collection_name}\n当前问题：${currentQuestion}\n候选人回答：${trimmed.slice(0, 3000)}`,
        },
      ]);
      const obj = extractJsonObject(aiText);
      if (obj) {
        if (typeof obj.depth_score === 'number') depth_score = Math.max(1, Math.min(10, Number(obj.depth_score)));
        if (typeof obj.is_vague === 'boolean') is_vague = obj.is_vague;
        if (typeof obj.need_followup === 'boolean') need_followup = obj.need_followup;
        if (obj.topic) nextTopic = String(obj.topic);
        if (obj.question) followupQuestion = String(obj.question);
        if (obj.followup_message) followupMessage = String(obj.followup_message);
      }
    } else {
      need_followup = depth_score <= 5;
      is_vague = depth_score <= 3;
    }

    const feedback = need_followup
      ? '你的回答方向正确，但还不够具体。建议补充技术选型依据、关键实现细节与量化结果。'
      : '你的回答较完整，逻辑清晰。下一题我会继续追问更深层的技术决策。';
    writeEvt('analysis_result', {
      depth_score,
      is_vague,
      need_followup,
      feedback,
      transcript,
    });
    await new Promise((r) => setTimeout(r, 120));

    if (need_followup) {
      writeEvt('followup', { message: followupMessage, transcript });
      await new Promise((r) => setTimeout(r, 120));
    }

    if (nextRound > INTERVIEW_MOCK_MAX_ROUNDS) {
      session.status = 'ended';
      session.total_rounds = round;
      writeEvt('interview_complete', {
        session_id: String(session_id),
        message: '面试已结束，可查看评估报告',
      });
      res.write('      \n\n');
      await new Promise((r) => setTimeout(r, 300));
      res.end();
      return;
    }

    session.total_rounds = nextRound;
    session.current_topic = nextTopic;
    session.current_question = followupQuestion;
    session.status = 'questioning';

    writeEvt('question', {
      answer: followupQuestion,
      question: followupQuestion,
      is_followup: need_followup,
      topic: nextTopic,
      round: nextRound,
      transcript,
    });
    // 与真实后端保持一致：结尾发送空白帧，减少客户端丢末尾块概率
    res.write('      \n\n');
    await new Promise((r) => setTimeout(r, 300));
    res.end();
  } catch (e) {
    console.error('新版 /interview/answer-voice 异常:', e);
    writeEvt('error', { message: e.message || '服务器错误' });
    res.end();
  }
});

app.get('/api/interview/session/:session_id/evaluation', authMiddleware, (req, res) => {
  const userId = String(req.user.id);
  const { session_id } = req.params;
  const session = interviewSessionsV2.get(String(session_id));
  if (!session || session.userId !== userId) {
    return res.status(404).json({ code: 404, message: '会话不存在或无权访问', data: null });
  }
  const data = {
    strengths: ['能够完成多轮技术问答，表达基本清晰。'],
    weaknesses: ['部分回答可结合更多项目细节与量化指标。'],
    session_id: String(session_id),
    overall_score: 7.5,
    recommendation: '推荐进入下一轮',
    overall_comment: '综合表现良好，建议结合业务场景继续深挖。',
    technical_evaluation: '技术栈与问题理解到位，可加强系统设计表述。',
    communication_evaluation: '沟通顺畅，逻辑结构可再条理一些。',
  };
  return res.json(ok200(data, 'success'));
});

app.get('/api/interview/session/:session_id', authMiddleware, (req, res) => {
  const userId = String(req.user.id);
  const { session_id } = req.params;
  const session = interviewSessionsV2.get(String(session_id));
  if (!session || session.userId !== userId) {
    return res.status(404).json({ code: 404, message: '会话不存在或无权访问', data: null });
  }
  return res.json(
    ok200({
      session_id: String(session_id),
      interview_mode: session.interview_mode || 'text',
      status: session.status,
      total_rounds: session.total_rounds,
      current_topic: session.current_topic,
      current_question: session.current_question,
      history: session.history || [],
    })
  );
});

app.delete('/api/interview/session/:session_id', authMiddleware, (req, res) => {
  const userId = String(req.user.id);
  const { session_id } = req.params;
  const session = interviewSessionsV2.get(String(session_id));
  if (!session || session.userId !== userId) {
    return res.status(404).json({ code: 404, message: '会话不存在或无权访问', data: null });
  }
  session.status = 'ended';
  interviewSessionsV2.delete(String(session_id));
  avatarInterviewSessions.delete(String(session_id));
  return res.json(ok200({ session_id: String(session_id), status: 'ended' }));
});

// ----- 虚拟人面试（方案A：后端鉴权，前端直连流媒体） -----
app.post('/api/interview/avatar/session/start', authMiddleware, (req, res) => {
  const userId = String(req.user.id);
  const { session_id, avatar_id } = req.body || {};
  if (!session_id) {
    return res.status(400).json({ code: 400, message: 'session_id 必填', data: null });
  }
  const interviewSession = interviewSessionsV2.get(String(session_id));
  if (!interviewSession || interviewSession.userId !== userId) {
    return res.status(404).json({ code: 404, message: '会话不存在或无权访问', data: null });
  }

  const avatar_session_id = crypto.randomUUID();
  const token = buildAvatarToken();
  const expire_at = Math.floor(Date.now() / 1000) + AVATAR_TOKEN_TTL_SEC;
  const pickedAvatarId = AVATAR_ALLOWED_IDS.has(String(avatar_id)) ? String(avatar_id) : '110592024';
  const sdk_config = buildAvatarSdkConfig(String(session_id), avatar_session_id, token, expire_at);
  avatarInterviewSessions.set(String(session_id), {
    userId,
    avatar_session_id,
    avatar_id: pickedAvatarId,
    token,
    expire_at,
    stream_url: sdk_config.stream_url,
    ws_url: sdk_config.ws_url,
    status: 'connected',
  });

  return res.json(
    ok200({
      session_id: String(session_id),
      avatar_session_id,
      vendor: AVATAR_VENDOR,
      avatar_id: pickedAvatarId,
      sdk_config,
    })
  );
});

app.post('/api/interview/avatar/session/refresh', authMiddleware, (req, res) => {
  const userId = String(req.user.id);
  const { session_id, avatar_session_id } = req.body || {};
  if (!session_id || !avatar_session_id) {
    return res.status(400).json({ code: 400, message: 'session_id 与 avatar_session_id 必填', data: null });
  }
  const item = avatarInterviewSessions.get(String(session_id));
  if (!item || item.userId !== userId || item.avatar_session_id !== String(avatar_session_id)) {
    return res.status(404).json({ code: 404, message: '虚拟人会话不存在或无权访问', data: null });
  }
  const token = buildAvatarToken();
  const expire_at = Math.floor(Date.now() / 1000) + AVATAR_TOKEN_TTL_SEC;
  item.token = token;
  item.expire_at = expire_at;
  const sdk_config = {
    token,
    expire_at,
  };
  return res.json(
    ok200({
      session_id: String(session_id),
      avatar_session_id: item.avatar_session_id,
      sdk_config,
    })
  );
});

app.post('/api/interview/avatar/speak', authMiddleware, (req, res) => {
  const userId = String(req.user.id);
  const { session_id, text, interrupt } = req.body || {};
  if (!session_id || !String(text || '').trim()) {
    return res.status(400).json({ code: 400, message: 'session_id 与 text 必填', data: null });
  }
  const interviewSession = interviewSessionsV2.get(String(session_id));
  if (!interviewSession || interviewSession.userId !== userId) {
    return res.status(404).json({ code: 404, message: '会话不存在或无权访问', data: null });
  }
  const avatarSession = avatarInterviewSessions.get(String(session_id));
  if (!avatarSession || avatarSession.userId !== userId) {
    return res.status(404).json({ code: 404, message: '虚拟人会话未初始化', data: null });
  }
  if (avatarSession.expire_at <= Math.floor(Date.now() / 1000)) {
    return res.status(401).json({ code: 401, message: '虚拟人凭证已过期，请先刷新会话', data: null });
  }
  const task_id = crypto.randomUUID();
  avatarSession.last_task = {
    task_id,
    text: String(text).trim(),
    interrupt: Boolean(interrupt),
    created_at: new Date().toISOString(),
  };
  return res.json(ok200({ accepted: true, task_id }));
});

app.delete('/api/interview/avatar/session/:session_id', authMiddleware, (req, res) => {
  const userId = String(req.user.id);
  const { session_id } = req.params;
  const item = avatarInterviewSessions.get(String(session_id));
  if (!item || item.userId !== userId) {
    return res.status(404).json({ code: 404, message: '虚拟人会话不存在或无权访问', data: null });
  }
  item.status = 'ended';
  avatarInterviewSessions.delete(String(session_id));
  return res.json(ok200({ session_id: String(session_id), status: 'ended' }));
});

app.listen(PORT, () => {
  console.log(`Backend server is running at http://localhost:${PORT}`);
  if (!ARK_API_KEY || !ARK_ENDPOINT_ID) {
    console.log(
      '[interview-ai] 未配置 ARK_API_KEY 或 ARK_ENDPOINT_ID，面试对话将使用本地模拟流式输出'
    );
  } else {
    console.log(
      `[interview-ai] 已启用方舟豆包流式：${ARK_CHAT_COMPLETIONS_URL}（model=${ARK_ENDPOINT_ID}）`
    );
  }
});
