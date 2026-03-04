/**
 * 批量插入模拟岗位数据到 job 表，用于本地开发演示和分页测试。
 * 使用方式：
 *  1. 在 backend 目录执行：node seed-mock-jobs.js
 *  2. 脚本会清空 job 表并插入多条计算机相关岗位数据
 */

/* eslint-disable @typescript-eslint/no-var-requires */
const pool = require('./db');

// 生成一批模拟岗位数据（中英文混合，覆盖不同岗位类型）
function buildMockJobs() {
  const baseJobs = [
    {
      name: 'Java 后端开发工程师',
      companyName: '字节跳动',
      salaryMin: 25000,
      salaryMax: 45000,
      jobContent:
        '负责后端服务开发与性能优化，参与系统架构设计，熟悉 Spring Boot / MySQL / Redis / 微服务。',
      type: 'backend',
    },
    {
      name: '高级 Java Backend Engineer',
      companyName: 'Alibaba',
      salaryMin: 30000,
      salaryMax: 50000,
      jobContent:
        'Design and develop large-scale backend services, familiar with Spring Cloud, MQ, distributed systems.',
      type: 'backend',
    },
    {
      name: 'Web 前端开发工程师',
      companyName: '腾讯',
      salaryMin: 20000,
      salaryMax: 40000,
      jobContent:
        '负责 Web 前端需求实现与性能优化，熟悉 Vue / React / TypeScript，具备良好组件化思维。',
      type: 'frontend',
    },
    {
      name: 'Frontend Engineer',
      companyName: 'Meituan',
      salaryMin: 18000,
      salaryMax: 35000,
      jobContent:
        'Implement user interfaces, optimize performance and user experience, familiar with modern frontend tooling.',
      type: 'frontend',
    },
    {
      name: 'Python 算法工程师',
      companyName: '华为',
      salaryMin: 28000,
      salaryMax: 48000,
      jobContent:
        '负责机器学习/深度学习模型研发与落地，熟悉常见算法与 PyTorch / TensorFlow。',
      type: 'algo',
    },
    {
      name: 'NLP Algorithm Engineer',
      companyName: 'Baidu',
      salaryMin: 26000,
      salaryMax: 46000,
      jobContent:
        'Work on NLP models, pre-training and fine-tuning, familiar with Transformer-based architectures.',
      type: 'algo',
    },
    {
      name: 'Fullstack Engineer',
      companyName: 'Xiaomi',
      salaryMin: 20000,
      salaryMax: 38000,
      jobContent:
        '负责 Web 全栈开发，掌握 Node.js / Vue / React，能够独立完成从前端到后端的功能实现。',
      type: 'fullstack',
    },
    {
      name: 'Go 后端开发工程师',
      companyName: '滴滴',
      salaryMin: 24000,
      salaryMax: 44000,
      jobContent:
        '参与高并发后台服务开发，熟悉 Go / MySQL / Redis / 微服务治理。',
      type: 'backend',
    },
    {
      name: 'C++ 游戏引擎工程师',
      companyName: '网易',
      salaryMin: 22000,
      salaryMax: 42000,
      jobContent:
        '负责游戏引擎与底层模块开发与优化，要求扎实的 C++ 基础和性能调优经验。',
      type: 'other',
    },
    {
      name: '前端可视化开发工程师',
      companyName: '字节跳动',
      salaryMin: 21000,
      salaryMax: 39000,
      jobContent:
        '负责数据可视化组件与大屏项目开发，熟悉 ECharts / WebGL / Canvas 等技术。',
      type: 'frontend',
    },
  ];

  // 复制多份基础岗位，稍作修改，生成更多数据以便测试分页
  const jobs = [];
  let idSuffix = 1;

  for (let round = 0; round < 3; round += 1) {
    for (const job of baseJobs) {
      jobs.push({
        ...job,
        name:
          round === 0
            ? job.name
            : `${job.name} (${round + 1})`,
        companyName: job.companyName,
        salaryMin: job.salaryMin,
        salaryMax: job.salaryMax,
        jobContent: job.jobContent,
        type: job.type,
        source: 'mock',
        sourceUrl: null,
        _idSuffix: idSuffix,
      });
      idSuffix += 1;
    }
  }

  return jobs;
}

async function seedJobs() {
  const jobs = buildMockJobs();
  const conn = await pool.getConnection();

  try {
    console.log(`开始写入模拟岗位数据，共 ${jobs.length} 条...`);
    await conn.beginTransaction();

    await conn.query('DELETE FROM job');

    const sql =
      'INSERT INTO job (name, company_name, company_logo, salary_min, salary_max, job_content, type, source, source_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)';

    for (const j of jobs) {
      await conn.query(sql, [
        j.name,
        j.companyName,
        null,
        j.salaryMin,
        j.salaryMax,
        j.jobContent,
        j.type,
        j.source,
        j.sourceUrl,
      ]);
    }

    await conn.commit();
    console.log('模拟岗位数据写入完成。');
  } catch (err) {
    await conn.rollback();
    console.error('写入 job 表失败:', err);
  } finally {
    conn.release();
  }
}

seedJobs()
  .then(() => {
    // eslint-disable-next-line no-process-exit
    process.exit(0);
  })
  .catch((err) => {
    console.error(err);
    // eslint-disable-next-line no-process-exit
    process.exit(1);
  });

