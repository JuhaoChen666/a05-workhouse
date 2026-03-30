/**
 * 从 Boss 直聘等网站爬取计算机相关岗位数据，写入 job 表，作为热门岗位和搜索的模拟数据。
 * 说明：
 * - 仅用于本地开发/学习环境，请遵守目标网站 robots 与服务条款，避免高频请求。
 * - 选择少量关键字 & 城市，控制抓取条数。
 */

/* eslint-disable @typescript-eslint/no-var-requires */
const cheerio = require('cheerio');
const fetch = (...args) => import('node-fetch').then(({ default: fetchFn }) => fetchFn(...args));
const pool = require('./db');

// 需要抓取的关键字与岗位类型映射
const KEYWORDS = [
  { keyword: 'Java开发', type: 'backend' },
  { keyword: 'Web前端', type: 'frontend' },
  { keyword: '算法工程师', type: 'algo' },
  { keyword: '全栈工程师', type: 'fullstack' },
];

// 简单的薪资字符串解析，例如「15-25K·14薪」-> { min: 15000, max: 25000 }
function parseSalary(text) {
  if (!text) return { min: null, max: null };
  const match = text.match(/(\d+)\s*-\s*(\d+)\s*K/i);
  if (!match) return { min: null, max: null };
  const min = parseInt(match[1], 10) * 1000;
  const max = parseInt(match[2], 10) * 1000;
  return { min, max };
}

// 从 Boss 直聘搜索页解析岗位列表（HTML 结构可能变更，如失效可根据实际页面调整选择器）
async function fetchJobsFromBoss(keyword, type, maxCount = 20) {
  const encoded = encodeURIComponent(keyword);
  const url = `https://www.zhipin.com/web/geek/job?query=${encoded}&city=101010100`;

  console.log(`开始抓取 Boss 直聘：${keyword} -> ${url}`);

  const res = await fetch(url, {
    headers: {
      'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36',
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    },
    timeout: 15000,
  });

  const html = await res.text();
  const $ = cheerio.load(html);

  const jobs = [];

  // 注意：以下选择器基于当前 Boss 直聘网页结构，后续可能需要调整
  $('.job-card-wrapper').each((_, el) => {
    if (jobs.length >= maxCount) return false;

    const $el = $(el);
    const title = $el.find('.job-title').text().trim();
    const companyName = $el.find('.company-name').text().trim();
    const salaryText = $el.find('.salary').text().trim();
    const linkPath = $el.find('a').attr('href') || '';
    const jobUrl = linkPath.startsWith('http') ? linkPath : `https://www.zhipin.com${linkPath}`;

    const desc = $el.find('.job-card-footer').text().trim();

    if (!title || !companyName) return;

    const { min, max } = parseSalary(salaryText);

    jobs.push({
      name: title,
      companyName,
      companyLogo: null,
      salaryMin: min,
      salaryMax: max,
      jobContent: desc || `${title} - ${companyName}`,
      type,
      source: 'boss',
      sourceUrl: jobUrl,
    });
  });

  console.log(`关键字「${keyword}」抓取到 ${jobs.length} 条岗位`);
  return jobs;
}

async function saveJobsToDb(jobs) {
  if (!jobs.length) return;

  const conn = await pool.getConnection();
  try {
    await conn.beginTransaction();

    // 简单策略：清空表后批量插入（仅用于模拟数据）
    await conn.query('DELETE FROM job');

    const sql =
      'INSERT INTO job (name, company_name, company_logo, salary_min, salary_max, job_content, type, source, source_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)';

    for (const j of jobs) {
      await conn.query(sql, [
        j.name,
        j.companyName,
        j.companyLogo,
        j.salaryMin,
        j.salaryMax,
        j.jobContent,
        j.type,
        j.source,
        j.sourceUrl,
      ]);
    }

    await conn.commit();
    console.log(`成功写入 job 表 ${jobs.length} 条记录`);
  } catch (err) {
    await conn.rollback();
    console.error('写入 job 表失败:', err);
    throw err;
  } finally {
    conn.release();
  }
}

async function main() {
  try {
    const allJobs = [];
    for (const item of KEYWORDS) {
      const list = await fetchJobsFromBoss(item.keyword, item.type, 20);
      allJobs.push(...list);
      // 简单限速
      await new Promise((r) => setTimeout(r, 3000));
    }

    await saveJobsToDb(allJobs);
    console.log('同步岗位数据完成');
  } catch (err) {
    console.error('同步岗位数据出错:', err);
  } finally {
    // 结束进程
    process.exit(0);
  }
}

if (require.main === module) {
  main();
}

