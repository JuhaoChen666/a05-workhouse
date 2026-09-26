/**
 * AI 面试平台 - 后端 API (Express)
 * 端口 3000，前缀 /api
 */
import express from 'express';
import cors from 'cors';
import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import multer from 'multer';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
const PORT = 3000;
const JWT_SECRET = process.env.JWT_SECRET || 'a05-workhouse-secret';
const UPLOAD_DIR = join(__dirname, 'uploads');

if (!fs.existsSync(UPLOAD_DIR)) fs.mkdirSync(UPLOAD_DIR, { recursive: true });

const storage = multer.diskStorage({
  destination: (_, __, cb) => cb(null, UPLOAD_DIR),
  filename: (_, file, cb) => cb(null, `avatar_${Date.now()}_${file.originalname || '.jpg'}`),
});
const upload = multer({ storage, limits: { fileSize: 2 * 1024 * 1024 } });

app.use(cors());
app.use(express.json());
app.use('/api/avatar-file', express.static(UPLOAD_DIR));

// ---------- 内存数据 ----------
let idSeq = { user: 2, position: 10, record: 1, report: 1, job: 20, question: 3, resource: 3 };
const users = [
  { id: '1', username: 'admin', password: bcrypt.hashSync('123456', 10), email: '', roleId: 2, roleName: '管理员', avatarUrl: null },
  { id: '1001', username: 'testuser', password: bcrypt.hashSync('123456', 10), email: 'a18058867190@163.com', roleId: 2, roleName: '管理员', avatarUrl: null },
];
const roles = [{ id: 1, name: '普通用户' }, { id: 2, name: '管理员' }];
const positions = [
  { id: 1, name: 'Java 后端开发', sortOrder: 0 },
  { id: 2, name: 'Web 前端开发', sortOrder: 1 },
  { id: 3, name: 'Python 算法工程师', sortOrder: 2 },
];
// 岗位扩展字段仅存放在内存中，用于模拟岗位详情与后台编辑
// key: positionId, value: { city, workExperience, ... }
const positionExtras = new Map();
const interviewRecords = [];
const reports = [];
const questionBank = [
  {
    id: 1,
    positionId: 2,
    question: '请介绍一个你负责的前端项目，以及你在其中解决的核心问题。',
    answer: '建议按背景、职责、方案、结果和复盘说明。',
    knowledgeTags: 'Vue, TypeScript, 项目经验',
  },
  {
    id: 2,
    positionId: 1,
    question: '如何定位并解决一个接口响应变慢的问题？',
    answer: '可以从链路、数据库、缓存、网络和代码性能几个层面排查。',
    knowledgeTags: '性能优化, 排障, 后端',
  },
];
const learningResources = [
  { id: 1, title: 'Vue 官方文档', link: 'https://vuejs.org/', tags: 'Vue, 前端' },
  { id: 2, title: 'TypeScript Handbook', link: 'https://www.typescriptlang.org/docs/', tags: 'TypeScript' },
];
const adminResumes = [];
const adminSessions = [];
const verificationCodes = new Map();
// 热门岗位（招聘信息）- 从网上整理的计算机相关招聘
// companyLogo 字段使用公司英文标识，前端通过 `/img/${companyLogo}.ico` 加载对应图标
const hotJobs = [
  { id: 1, name: 'Java 后端开发工程师', companyName: '字节跳动', companyLogo: 'ByteDance', salaryMin: 25000, salaryMax: 45000, jobContent: '负责后端服务与复杂应用的设计、开发和维护；参与系统性能优化和架构设计；与前端协作实现业务逻辑；要求熟悉 Java、Spring Boot、MySQL、Redis、微服务。' },
  { id: 2, name: '高级 Java 开发工程师', companyName: '阿里巴巴', companyLogo: 'Alibaba', salaryMin: 30000, salaryMax: 50000, jobContent: '负责电商/云计算相关后端系统开发；参与分布式系统设计与优化；要求 3 年以上 Java 经验，熟悉 Spring Cloud、MQ、Kafka。' },
  { id: 3, name: 'Web 前端开发工程师', companyName: '腾讯', companyLogo: 'Tencent', salaryMin: 20000, salaryMax: 40000, jobContent: '负责前端需求分析、架构设计和代码开发；与产品、设计、后端协作完成页面与功能；熟练掌握 Vue/React、TypeScript、前端工程化。' },
  { id: 4, name: '前端开发工程师', companyName: '美团', companyLogo: 'Meituan', salaryMin: 18000, salaryMax: 35000, jobContent: '负责业务前端开发与组件库维护；优化前端性能与体验；要求精通 HTML5/CSS3/JavaScript，有 Vue 或 React 项目经验。' },
  { id: 5, name: 'Python 算法工程师', companyName: '华为', companyLogo: 'Huawei', salaryMin: 28000, salaryMax: 48000, jobContent: '负责机器学习/深度学习模型研发与落地；参与数据处理与算法优化；要求熟悉 Python、TensorFlow/PyTorch、常用 ML 算法。' },
  { id: 6, name: 'C++ 开发工程师', companyName: '网易', companyLogo: 'NetEase', salaryMin: 22000, salaryMax: 42000, jobContent: '负责游戏或基础组件开发；性能优化与跨平台适配；要求扎实的 C++ 基础，有大型项目经验优先。' },
  { id: 7, name: 'Go 后端开发', companyName: '滴滴', companyLogo: 'Didi', salaryMin: 24000, salaryMax: 44000, jobContent: '负责高并发后端服务开发；参与微服务架构设计；要求熟悉 Go、MySQL、Redis、K8s。' },
  { id: 8, name: '全栈开发工程师', companyName: '小米', companyLogo: 'Xiaomi', salaryMin: 20000, salaryMax: 38000, jobContent: '负责 Web 全栈功能开发；前后端联调与部署；要求熟悉 Node/Vue 或 React，有后端经验。' },
];

function resOk(data = null) {
  return { code: 0, message: 'ok', data };
}
function resErr(code, message) {
  return { code, message, data: null };
}

function authMiddleware(req, res, next) {
  const raw = req.headers.authorization;
  const token = raw && raw.startsWith('Bearer ') ? raw.slice(7) : null;
  if (!token) return res.json(resErr(401, '未提供 token'));
  try {
    const payload = jwt.verify(token, JWT_SECRET);
    req.userId = payload.id;
    req.roleId = payload.roleId;
    next();
  } catch {
    return res.json(resErr(401, 'token 无效或已过期'));
  }
}

function getPositionName(positionId) {
  const p = positions.find((x) => x.id === positionId);
  return p ? p.name : '';
}

// ---------- 路由：认证 ----------
app.post('/api/auth/register', (req, res) => {
  const { username, password, confirmPassword, email = '' } = req.body || {};
  if (!username || !password) return res.json(resErr(1001, '用户名或密码不能为空'));
  if (password !== confirmPassword) return res.json(resErr(1002, '两次密码不一致'));
  if (users.some((u) => u.username === username)) return res.json(resErr(1003, '用户名已存在'));
  const id = String(++idSeq.user);
  users.push({
    id,
    username,
    password: bcrypt.hashSync(password, 10),
    email: String(email || '').trim(),
    roleId: 1,
    roleName: '普通用户',
    avatarUrl: null,
  });
  return res.json(resOk(null));
});

app.post('/api/auth/login', (req, res) => {
  const { username, password } = req.body || {};
  if (!username || !password) return res.json(resErr(1001, '用户名或密码不能为空'));
  const user = users.find((u) => u.username === username);
  if (!user || !bcrypt.compareSync(password, user.password))
    return res.json(resErr(1004, '用户名或密码错误'));
  const token = jwt.sign(
    // FastAPI's shared resume auth contract requires a numeric owner id.
    { id: Number(user.id), username: user.username, roleId: Number(user.roleId) },
    JWT_SECRET,
    { expiresIn: '2h' }
  );
  return res.json(resOk({
    token,
    user: {
      id: user.id,
      username: user.username,
      roleId: user.roleId,
      roleName: user.roleName,
      email: user.email,
      avatarUrl: user.avatarUrl,
    },
  }));
});

app.get('/api/auth/profile', authMiddleware, (req, res) => {
  const user = users.find((u) => u.id === String(req.userId));
  if (!user) return res.json(resErr(1005, '用户不存在'));
  const role = roles.find((r) => r.id === user.roleId);
  return res.json(resOk({
    id: user.id,
    username: user.username,
    email: user.email,
    roleId: user.roleId,
    roleName: (role && role.name) || '普通用户',
    avatarUrl: user.avatarUrl,
  }));
});

app.put('/api/auth/password', authMiddleware, (req, res) => {
  const { oldPassword, newPassword, confirmPassword } = req.body || {};
  if (newPassword !== confirmPassword) return res.json(resErr(1002, '两次新密码不一致'));
  const user = users.find((u) => u.id === String(req.userId));
  if (!user) return res.json(resErr(1005, '用户不存在'));
  if (!bcrypt.compareSync(oldPassword, user.password)) return res.json(resErr(1006, '原密码错误'));
  user.password = bcrypt.hashSync(newPassword, 10);
  return res.json(resOk(null));
});

app.post('/api/auth/avatar', authMiddleware, upload.single('file'), (req, res) => {
  const user = users.find((u) => u.id === String(req.userId));
  if (!user) return res.json(resErr(1005, '用户不存在'));
  if (req.file) {
    const avatarUrl = `/api/avatar-file/${req.file.filename}`;
    user.avatarUrl = avatarUrl;
    return res.json(resOk({ avatarUrl }));
  }
  const { avatar: base64 } = req.body || {};
  if (base64) {
    const match = base64.match(/^data:image\/\w+;base64,(.+)$/);
    const buf = match ? Buffer.from(match[1], 'base64') : Buffer.from(base64, 'base64');
    const filename = `avatar_${req.userId}_${Date.now()}.png`;
    const filepath = join(UPLOAD_DIR, filename);
    fs.writeFileSync(filepath, buf);
    const avatarUrl = `/api/avatar-file/${filename}`;
    user.avatarUrl = avatarUrl;
    return res.json(resOk({ avatarUrl }));
  }
  return res.json(resErr(400, '请上传图片或传 base64'));
});

// 管理端头像兼容接口：前端文档使用 /api/admin/users/:id/avatar，
// 本机 Mock 复用登录用户的头像存储逻辑，避免页面因接口契约差异报 404。
app.get('/api/admin/users/:id/avatar', authMiddleware, (req, res) => {
  const user = users.find((u) => u.id === String(req.params.id));
  if (!user) return res.json(resErr(1005, '用户不存在'));
  return res.json(resOk({ avatarUrl: user.avatarUrl || '' }));
});

app.post('/api/admin/users/:id/avatar', authMiddleware, upload.single('file'), (req, res) => {
  const user = users.find((u) => u.id === String(req.params.id));
  if (!user) return res.json(resErr(1005, '用户不存在'));
  if (String(req.userId) !== user.id && Number(req.roleId) !== 2) {
    return res.json(resErr(403, '无权修改该用户头像'));
  }
  if (!req.file) return res.json(resErr(400, '请上传图片'));
  const avatarUrl = `/api/avatar-file/${req.file.filename}`;
  user.avatarUrl = avatarUrl;
  return res.json(resOk({ avatarUrl }));
});

function adminMiddleware(req, res, next) {
  authMiddleware(req, res, () => {
    if (Number(req.roleId) !== 2) return res.json(resErr(403, '仅管理员可访问'));
    next();
  });
}

function userView(user) {
  return {
    id: Number(user.id),
    username: user.username,
    email: user.email || '',
    avatar: user.avatarUrl || '',
    avatarUrl: user.avatarUrl || '',
    roleId: user.roleId,
    roleName: user.roleName,
  };
}

// ---------- 本机管理端兼容接口 ----------
app.get('/api/admin/users', adminMiddleware, (req, res) => {
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const pageSize = Math.min(100, Math.max(1, parseInt(req.query.pageSize, 10) || 10));
  const list = users.map(userView);
  const start = (page - 1) * pageSize;
  return res.json(resOk({ list: list.slice(start, start + pageSize), total: list.length, page, pageSize }));
});

app.get('/api/admin/users/:id', adminMiddleware, (req, res) => {
  const user = users.find((item) => item.id === String(req.params.id));
  if (!user) return res.json(resErr(404, '用户不存在'));
  return res.json(resOk(userView(user)));
});

app.post('/api/admin/users', adminMiddleware, (req, res) => {
  const { username, password, email = '', roleId = 1 } = req.body || {};
  if (!String(username || '').trim() || !String(password || '').trim()) {
    return res.json(resErr(400, '用户名和密码不能为空'));
  }
  if (users.some((item) => item.username === username)) return res.json(resErr(409, '用户名已存在'));
  const user = {
    id: String(++idSeq.user),
    username: String(username).trim(),
    password: bcrypt.hashSync(String(password), 10),
    email: String(email || '').trim(),
    roleId: Number(roleId) === 2 ? 2 : 1,
    roleName: Number(roleId) === 2 ? '管理员' : '普通用户',
    avatarUrl: null,
  };
  users.push(user);
  return res.json(resOk(userView(user)));
});

app.put('/api/admin/users/:id', adminMiddleware, (req, res) => {
  const user = users.find((item) => item.id === String(req.params.id));
  if (!user) return res.json(resErr(404, '用户不存在'));
  const { username, email, roleId, password } = req.body || {};
  if (username !== undefined) user.username = String(username).trim();
  if (email !== undefined) user.email = String(email || '').trim();
  if (roleId !== undefined) {
    user.roleId = Number(roleId) === 2 ? 2 : 1;
    user.roleName = user.roleId === 2 ? '管理员' : '普通用户';
  }
  if (password) user.password = bcrypt.hashSync(String(password), 10);
  return res.json(resOk(userView(user)));
});

app.delete('/api/admin/users/:id', adminMiddleware, (req, res) => {
  const index = users.findIndex((item) => item.id === String(req.params.id));
  if (index < 0) return res.json(resErr(404, '用户不存在'));
  if (users[index].id === String(req.userId)) return res.json(resErr(409, '不能删除当前登录用户'));
  users.splice(index, 1);
  return res.json(resOk(null));
});

// Local-only verification flow: deterministic code keeps registration and
// password recovery testable without SMTP or another external service.
app.post('/api/auth/send-code', (req, res) => {
  const { username = '', email = '', scene = 'reset' } = req.body || {};
  const key = `${scene}:${String(username).trim()}:${String(email).trim().toLowerCase()}`;
  verificationCodes.set(key, { code: '123456', expiresAt: Date.now() + 10 * 60 * 1000 });
  return res.json(resOk({ code: '123456', expiresIn: 600, local: true }));
});

app.post('/api/auth/verify-code', (req, res) => {
  const { username = '', email = '', code, newpassword, newPassword, confirmPassword } = req.body || {};
  const password = newpassword || newPassword;
  const user = users.find((item) =>
    item.username === String(username).trim() ||
    (email && item.email && item.email.toLowerCase() === String(email).trim().toLowerCase())
  );
  if (!user) return res.json(resErr(1005, '用户不存在'));
  if (!password || password !== confirmPassword) return res.json(resErr(1002, '两次新密码不一致'));
  const key = `reset:${String(username).trim()}:${String(email).trim().toLowerCase()}`;
  const saved = verificationCodes.get(key);
  if (String(code || '') !== '123456' && (!saved || saved.expiresAt < Date.now() || saved.code !== String(code))) {
    return res.json(resErr(1009, '验证码错误或已过期'));
  }
  user.password = bcrypt.hashSync(String(password), 10);
  verificationCodes.delete(key);
  return res.json(resOk(null));
});

// The frontend uses POST for the authenticated password-change flow.
app.post('/api/auth/password', authMiddleware, (req, res) => {
  const { oldPassword, newPassword, confirmPassword } = req.body || {};
  const user = users.find((u) => u.id === String(req.userId));
  if (!user) return res.json(resErr(1005, '用户不存在'));
  if (newPassword !== confirmPassword) return res.json(resErr(1002, '两次新密码不一致'));
  if (req.body?.code && String(req.body.code) !== '123456') return res.json(resErr(1009, '验证码错误或已过期'));
  if (!bcrypt.compareSync(oldPassword, user.password)) return res.json(resErr(1006, '原密码错误'));
  user.password = bcrypt.hashSync(newPassword, 10);
  return res.json(resOk(null));
});

function adminPositionView(position) {
  const extra = positionExtras.get(position.id) || {};
  return {
    id: position.id,
    name: position.name,
    sortOrder: position.sortOrder,
    sort_order: position.sortOrder,
    ...extra,
  };
}

app.get('/api/admin/positions/page', adminMiddleware, (req, res) => {
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const pageSize = Math.min(100, Math.max(1, parseInt(req.query.pageSize, 10) || 10));
  const keyword = String(req.query.name || '').trim().toLowerCase();
  const all = positions
    .map(adminPositionView)
    .filter((item) => !keyword || item.name.toLowerCase().includes(keyword));
  const start = (page - 1) * pageSize;
  return res.json(resOk({ list: all.slice(start, start + pageSize), total: all.length, page, pageSize }));
});

app.get('/api/admin/positions/:id', adminMiddleware, (req, res) => {
  const position = positions.find((item) => item.id === Number(req.params.id));
  if (!position) return res.json(resErr(404, '岗位不存在'));
  return res.json(resOk(adminPositionView(position)));
});

app.post('/api/admin/positions', adminMiddleware, (req, res) => {
  const name = String(req.body?.name || '').trim();
  if (!name) return res.json(resErr(400, '岗位名称不能为空'));
  const position = { id: ++idSeq.position, name, sortOrder: Number(req.body?.sort_order ?? 0) || 0 };
  positions.push(position);
  return res.json(resOk(adminPositionView(position)));
});

function savePositionInfo(req, res) {
  const body = req.body || {};
  const id = Number(body.id);
  const position = positions.find((item) => item.id === id);
  if (!position) return res.json(resErr(404, '岗位不存在'));
  if (body.name !== undefined) position.name = String(body.name).trim();
  positionExtras.set(id, {
    ...(positionExtras.get(id) || {}),
    responsibility: String(body.responsibility || ''),
    responsibilities: String(body.responsibility || ''),
    salary_junior: String(body.salary_junior || ''),
    salary_mid: String(body.salary_mid || ''),
    salary_senior: String(body.salary_senior || ''),
    salary_expert: String(body.salary_expert || ''),
    skill_requirements: String(body.skill_requirements || ''),
    requirements: String(body.skill_requirements || ''),
  });
  return res.json(resOk(adminPositionView(position)));
}

app.post('/api/admin/positions/info', adminMiddleware, savePositionInfo);
app.put('/api/admin/positions/info', adminMiddleware, savePositionInfo);
app.put('/api/admin/positions/:id', adminMiddleware, (req, res) => {
  return savePositionInfo({ ...req, body: { ...(req.body || {}), id: Number(req.params.id) } }, res);
});
app.delete('/api/admin/positions/:id', adminMiddleware, (req, res) => {
  const id = Number(req.params.id);
  const index = positions.findIndex((item) => item.id === id);
  if (index < 0) return res.json(resErr(404, '岗位不存在'));
  positions.splice(index, 1);
  positionExtras.delete(id);
  return res.json(resOk(null));
});

function pagedRows(rows, req) {
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const pageSize = Math.min(100, Math.max(1, parseInt(req.query.pageSize, 10) || 10));
  const start = (page - 1) * pageSize;
  return { list: rows.slice(start, start + pageSize), total: rows.length, page, pageSize };
}

app.get('/api/admin/resumes/page', adminMiddleware, (req, res) => {
  const userId = req.query.userId ? Number(req.query.userId) : null;
  const rows = userId ? adminResumes.filter((item) => item.userId === userId) : adminResumes;
  return res.json(resOk(pagedRows(rows, req)));
});
app.delete('/api/admin/resumes/:id', adminMiddleware, (req, res) => {
  const index = adminResumes.findIndex((item) => item.id === Number(req.params.id));
  if (index >= 0) adminResumes.splice(index, 1);
  return res.json(resOk(null));
});
app.get('/api/admin/sessions/page', adminMiddleware, (req, res) => {
  const userId = req.query.userId ? Number(req.query.userId) : null;
  const rows = userId ? adminSessions.filter((item) => item.userId === userId) : adminSessions;
  return res.json(resOk(pagedRows(rows, req)));
});
app.delete('/api/admin/sessions/:id', adminMiddleware, (req, res) => {
  const index = adminSessions.findIndex((item) => item.sessionId === String(req.params.id));
  if (index >= 0) adminSessions.splice(index, 1);
  return res.json(resOk(null));
});

// ---------- 角色、岗位（面试用） ----------
app.get('/api/roles', authMiddleware, (_, res) => {
  return res.json(resOk(roles.map((r) => ({ id: r.id, name: r.name }))));
});

app.get('/api/positions', authMiddleware, (_, res) => {
  const list = [...positions].sort((a, b) => a.sortOrder - b.sortOrder || a.id - b.id);
  // 将内存中的扩展字段合并到列表中，方便后台管理表单回显
  const merged = list.map((p) => {
    const extra = positionExtras.get(p.id) || {};
    return { id: p.id, name: p.name, sortOrder: p.sortOrder, ...extra };
  });
  return res.json(resOk(merged));
});

app.get('/api/positions/simple/page', authMiddleware, (req, res) => {
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const pageSize = Math.min(100, Math.max(1, parseInt(req.query.pageSize, 10) || 10));
  const keyword = String(req.query.name || '').trim().toLowerCase();
  const all = positions
    .filter((item) => !keyword || item.name.toLowerCase().includes(keyword))
    .sort((a, b) => a.sortOrder - b.sortOrder || a.id - b.id)
    .map((item) => ({
      id: item.id,
      name: item.name,
      englishName: item.name.replace(/\s+/g, '-').toLowerCase(),
      responsibility: positionExtras.get(item.id)?.responsibility || '',
    }));
  const start = (page - 1) * pageSize;
  return res.json(resOk({ total: all.length, pageSize, page, list: all.slice(start, start + pageSize) }));
});

// ---------- 面试记录 ----------
app.post('/api/interview-record', authMiddleware, (req, res) => {
  const { positionId } = req.body || {};
  if (!positionId) return res.json(resErr(400, '岗位必选'));
  const id = idSeq.record++;
  const record = {
    id,
    userId: req.userId,
    positionId: Number(positionId),
    positionName: getPositionName(Number(positionId)),
    startedAt: new Date().toISOString(),
    endedAt: null,
    totalScore: null,
  };
  interviewRecords.push(record);
  return res.json(resOk({ id: record.id, userId: record.userId, positionId: record.positionId, startedAt: record.startedAt }));
});

// 后台 / 详情页用到的岗位详情（包含扩展字段）
app.get('/api/positions/:id', authMiddleware, (req, res) => {
  const id = parseInt(req.params.id, 10);
  const p = positions.find((x) => x.id === id);
  if (!p) return res.json(resErr(404, '岗位不存在'));

  const extra = positionExtras.get(id) || {};
  const q = req.query || {};

  const detail = {
    id: p.id,
    name: p.name,
    sortOrder: p.sortOrder,
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

  return res.json(resOk(detail));
});

app.get('/api/interview-record', authMiddleware, (req, res) => {
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const pageSize = Math.min(50, Math.max(1, parseInt(req.query.pageSize, 10) || 10));
  const list = interviewRecords
    .filter((r) => r.userId === req.userId)
    .sort((a, b) => new Date(b.startedAt) - new Date(a.startedAt));
  const total = list.length;
  const start = (page - 1) * pageSize;
  const slice = list.slice(start, start + pageSize).map((r) => ({
    id: r.id,
    positionId: r.positionId,
    positionName: r.positionName,
    startedAt: r.startedAt,
    endedAt: r.endedAt,
    totalScore: r.totalScore,
  }));
  return res.json(resOk({ list: slice, total }));
});

app.get('/api/interview-record/stats', authMiddleware, (req, res) => {
  const list = interviewRecords.filter((r) => r.userId === req.userId && r.endedAt != null);
  const totalCount = interviewRecords.filter((r) => r.userId === req.userId).length;
  const finishedCount = list.length;
  const scores = list.map((r) => r.totalScore).filter((s) => s != null);
  const avgScore = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null;
  const last = interviewRecords.filter((r) => r.userId === req.userId).sort((a, b) => new Date(b.startedAt) - new Date(a.startedAt))[0];
  return res.json(resOk({
    totalCount,
    finishedCount,
    avgScore: avgScore != null ? Math.round(avgScore * 10) / 10 : null,
    lastAt: last ? last.startedAt : null,
  }));
});

app.get('/api/interview-record/recent-scores', authMiddleware, (req, res) => {
  const limit = Math.min(20, Math.max(1, parseInt(req.query.limit, 10) || 10));
  const list = interviewRecords
    .filter((r) => r.userId === req.userId && r.endedAt != null && r.totalScore != null)
    .sort((a, b) => new Date(b.startedAt) - new Date(a.startedAt))
    .slice(0, limit)
    .map((r) => ({
      interviewRecordId: r.id,
      positionName: r.positionName,
      startedAt: r.startedAt,
      totalScore: r.totalScore,
    }));
  return res.json(resOk(list));
});

app.get('/api/interview-record/:id', authMiddleware, (req, res) => {
  const id = parseInt(req.params.id, 10);
  const r = interviewRecords.find((x) => x.id === id);
  if (!r) return res.json(resErr(404, '记录不存在'));
  if (r.userId !== req.userId && req.roleId !== 2) return res.json(resErr(403, '无权限'));
  return res.json(resOk({ ...r, details: [] }));
});

app.patch('/api/interview-record/:id/end', authMiddleware, (req, res) => {
  const id = parseInt(req.params.id, 10);
  const r = interviewRecords.find((x) => x.id === id);
  if (!r) return res.json(resErr(404, '记录不存在'));
  if (r.userId !== req.userId) return res.json(resErr(403, '无权限'));
  r.endedAt = (req.body && req.body.endedAt) || new Date().toISOString();
  r.totalScore = req.body && req.body.totalScore != null ? req.body.totalScore : (r.totalScore ?? 72);
  return res.json(resOk(null));
});

// ---------- 报告 ----------
app.get('/api/report', authMiddleware, (req, res) => {
  const interviewRecordId = parseInt(req.query.interviewRecordId, 10);
  if (!interviewRecordId) return res.json(resErr(400, '缺少 interviewRecordId'));
  const r = interviewRecords.find((x) => x.id === interviewRecordId);
  if (!r) return res.json(resErr(404, '记录不存在'));
  if (r.userId !== req.userId && req.roleId !== 2) return res.json(resErr(403, '无权限'));
  const rep = reports.find((x) => x.interviewRecordId === interviewRecordId);
  if (!rep) {
    const content = {
      totalScore: r.totalScore ?? 75,
      dimensions: [
        { name: '技术深度', score: 78, comment: '基础扎实' },
        { name: '表达清晰度', score: 72, comment: '条理清晰' },
        { name: '逻辑性', score: 80, comment: '逻辑较好' },
        { name: '岗位匹配度', score: 75, comment: '基本匹配' },
      ],
      summary: '整体表现良好，建议加强项目深挖与场景设计。',
      suggestions: ['多准备项目难点与优化案例', '熟悉常见中间件原理'],
    };
    return res.json(resOk({ id: 0, interviewRecordId, content }));
  }
  return res.json(resOk(rep));
});

app.post('/api/report', authMiddleware, (req, res) => {
  const { interviewRecordId, content } = req.body || {};
  if (interviewRecordId == null) return res.json(resErr(400, '缺少 interviewRecordId'));
  const r = interviewRecords.find((x) => x.id === interviewRecordId);
  if (!r) return res.json(resErr(404, '记录不存在'));
  if (r.userId !== req.userId) return res.json(resErr(403, '无权限'));
  let rep = reports.find((x) => x.interviewRecordId === interviewRecordId);
  if (!rep) {
    rep = { id: idSeq.report++, interviewRecordId, content };
    reports.push(rep);
  } else {
    rep.content = content;
  }
  return res.json(resOk(rep));
});

// ---------- 用户能力分析 ----------
app.get('/api/user/ability-analysis', authMiddleware, (req, res) => {
  const list = interviewRecords.filter((r) => r.userId === req.userId && r.totalScore != null);
  const avg = list.length ? list.reduce((s, r) => s + r.totalScore, 0) / list.length : 70;
  const bar = [
    { name: '技术深度', value: Math.round(avg * 0.95 + Math.random() * 10) },
    { name: '表达清晰度', value: Math.round(avg * 0.9 + Math.random() * 12) },
    { name: '逻辑性', value: Math.round(avg * 1.0 + Math.random() * 8) },
    { name: '岗位匹配度', value: Math.round(avg * 0.92 + Math.random() * 10) },
    { name: '应变能力', value: Math.round(avg * 0.88 + Math.random() * 14) },
  ];
  const radar = [
    { name: '技术深度', value: bar[0].value, max: 100 },
    { name: '表达清晰度', value: bar[1].value, max: 100 },
    { name: '逻辑性', value: bar[2].value, max: 100 },
    { name: '岗位匹配度', value: bar[3].value, max: 100 },
    { name: '应变能力', value: bar[4].value, max: 100 },
  ];
  return res.json(resOk({ bar, radar }));
});

// ---------- 热门岗位（招聘） ----------
app.get('/api/jobs/hot', authMiddleware, (req, res) => {
  const limit = Math.min(20, Math.max(1, parseInt(req.query.limit, 10) || 10));
  const list = hotJobs.slice(0, limit).map((j) => ({
    id: j.id,
    name: j.name,
    companyName: j.companyName,
    companyLogo: j.companyLogo,
    salaryMin: j.salaryMin,
    salaryMax: j.salaryMax,
    jobContent: j.jobContent,
  }));
  return res.json(resOk(list));
});

app.get('/api/jobs/:id', authMiddleware, (req, res) => {
  const id = parseInt(req.params.id, 10);
  const j = hotJobs.find((x) => x.id === id);
  if (!j) return res.json(resErr(404, '岗位不存在'));
  return res.json(resOk({
    id: j.id,
    name: j.name,
    companyName: j.companyName,
    companyLogo: j.companyLogo,
    salaryMin: j.salaryMin,
    salaryMax: j.salaryMax,
    jobContent: j.jobContent,
  }));
});

app.get('/api/jobs/search', authMiddleware, (req, res) => {
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const pageSize = Math.min(100, Math.max(1, parseInt(req.query.pageSize, 10) || 10));
  const keyword = String(req.query.keyword || '').trim().toLowerCase();
  const type = String(req.query.type || '').trim().toLowerCase();
  const rows = hotJobs.filter((job) => {
    const matchesKeyword = !keyword ||
      `${job.name} ${job.companyName} ${job.jobContent}`.toLowerCase().includes(keyword);
    const matchesType = !type || String(job.type || '').toLowerCase() === type;
    return matchesKeyword && matchesType;
  });
  const start = (page - 1) * pageSize;
  return res.json(resOk({ list: rows.slice(start, start + pageSize), total: rows.length, page, pageSize }));
});

// ---------- 题库与学习资源兼容接口 ----------
function questionView(item) {
  const position = positions.find((row) => row.id === item.positionId);
  return { ...item, positionName: position?.name || '' };
}
app.get('/api/question-bank', authMiddleware, (req, res) => {
  const positionId = req.query.positionId ? Number(req.query.positionId) : null;
  const rows = questionBank.filter((item) => !positionId || item.positionId === positionId).map(questionView);
  return res.json(resOk(pagedRows(rows, req)));
});
app.get('/api/question-bank/:id', authMiddleware, (req, res) => {
  const item = questionBank.find((row) => row.id === Number(req.params.id));
  return item ? res.json(resOk(questionView(item))) : res.json(resErr(404, '题目不存在'));
});
app.post('/api/question-bank', adminMiddleware, (req, res) => {
  const body = req.body || {};
  if (!body.positionId || !String(body.question || '').trim()) return res.json(resErr(400, '岗位和题目不能为空'));
  const item = {
    id: idSeq.question++,
    positionId: Number(body.positionId),
    question: String(body.question).trim(),
    answer: body.answer == null ? null : String(body.answer),
    knowledgeTags: body.knowledgeTags == null ? null : String(body.knowledgeTags),
  };
  questionBank.push(item);
  return res.json(resOk(questionView(item)));
});
app.put('/api/question-bank/:id', adminMiddleware, (req, res) => {
  const item = questionBank.find((row) => row.id === Number(req.params.id));
  if (!item) return res.json(resErr(404, '题目不存在'));
  const body = req.body || {};
  if (body.positionId !== undefined) item.positionId = Number(body.positionId);
  if (body.question !== undefined) item.question = String(body.question);
  if (body.answer !== undefined) item.answer = body.answer == null ? null : String(body.answer);
  if (body.knowledgeTags !== undefined) item.knowledgeTags = body.knowledgeTags == null ? null : String(body.knowledgeTags);
  return res.json(resOk(questionView(item)));
});
app.delete('/api/question-bank/:id', adminMiddleware, (req, res) => {
  const index = questionBank.findIndex((row) => row.id === Number(req.params.id));
  if (index < 0) return res.json(resErr(404, '题目不存在'));
  questionBank.splice(index, 1);
  return res.json(resOk(null));
});

app.get('/api/learning-resource', authMiddleware, (req, res) => {
  return res.json(resOk(pagedRows(learningResources, req)));
});
app.post('/api/learning-resource', adminMiddleware, (req, res) => {
  const body = req.body || {};
  if (!String(body.title || '').trim() || !String(body.link || '').trim()) {
    return res.json(resErr(400, '标题和链接不能为空'));
  }
  const item = { id: idSeq.resource++, title: String(body.title).trim(), link: String(body.link).trim(), tags: String(body.tags || '') };
  learningResources.push(item);
  return res.json(resOk(item));
});
app.put('/api/learning-resource/:id', adminMiddleware, (req, res) => {
  const item = learningResources.find((row) => row.id === Number(req.params.id));
  if (!item) return res.json(resErr(404, '资源不存在'));
  const body = req.body || {};
  if (body.title !== undefined) item.title = String(body.title);
  if (body.link !== undefined) item.link = String(body.link);
  if (body.tags !== undefined) item.tags = String(body.tags || '');
  return res.json(resOk(item));
});
app.delete('/api/learning-resource/:id', adminMiddleware, (req, res) => {
  const index = learningResources.findIndex((row) => row.id === Number(req.params.id));
  if (index < 0) return res.json(resErr(404, '资源不存在'));
  learningResources.splice(index, 1);
  return res.json(resOk(null));
});

app.get('/health', (_, res) => {
  return res.json({ status: 'healthy', service: 'node-local' });
});

// ---------- 启动 ----------
app.listen(PORT, () => {
  console.log(`API server http://localhost:${PORT}/api`);
});
