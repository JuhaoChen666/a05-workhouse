package com.example.springbootbackend.Controller;

import com.example.springbootbackend.entity.Job;
import com.example.springbootbackend.service.JobService;
import com.example.springbootbackend.utils.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
public class JobController {
    @Autowired
    private JobService jobService;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @GetMapping("/jobs")
    public Result getAllJobs() {
        return Result.success(jobService.getAllJobs());

    }

    @GetMapping("/jobs/hot")
    public Result getHotJobs(@RequestParam(required = false, defaultValue = "6") int limit) {
        int safeLimit = Math.max(1, Math.min(limit, 50));
        List<Map<String, Object>> jobs = jdbcTemplate.queryForList(
                "SELECT id, name, companyName, companyLogo, salaryMin, salaryMax, jobContent, type FROM job ORDER BY id ASC LIMIT ?",
                safeLimit
        );
        return Result.success(jobs);
    }

    @GetMapping("/jobs/search")
    public Result searchJobs(@RequestParam(required = false, defaultValue = "") String keyword,
                             @RequestParam(required = false, defaultValue = "") String type,
                             @RequestParam(defaultValue = "1") int page,
                             @RequestParam(defaultValue = "8") int pageSize) {
        int safePage = Math.max(1, page);
        int safePageSize = Math.max(1, Math.min(pageSize, 50));
        int offset = (safePage - 1) * safePageSize;
        String kw = "%" + keyword.trim() + "%";
        String typeValue = type.trim();
        boolean hasType = !typeValue.isEmpty();

        String where = " WHERE (name LIKE ? OR companyName LIKE ? OR jobContent LIKE ?)";
        if (hasType) {
            where += " AND type = ?";
        }
        String countSql = "SELECT COUNT(*) FROM job" + where;
        String listSql = "SELECT id, name, companyName, companyLogo, salaryMin, salaryMax, jobContent, type FROM job"
                + where + " ORDER BY id ASC LIMIT ? OFFSET ?";

        Long total;
        List<Map<String, Object>> list;
        if (hasType) {
            total = jdbcTemplate.queryForObject(countSql, Long.class, kw, kw, kw, typeValue);
            list = jdbcTemplate.queryForList(listSql, kw, kw, kw, typeValue, safePageSize, offset);
        } else {
            total = jdbcTemplate.queryForObject(countSql, Long.class, kw, kw, kw);
            list = jdbcTemplate.queryForList(listSql, kw, kw, kw, safePageSize, offset);
        }

        Map<String, Object> data = new HashMap<>();
        data.put("list", list);
        data.put("total", total == null ? 0 : total);
        return Result.success(data);
    }

    @GetMapping("/jobs/{id}")
    public Result getJobById(@PathVariable Integer id) {
        return Result.success(jobService.getJobById(id));
    }
}
