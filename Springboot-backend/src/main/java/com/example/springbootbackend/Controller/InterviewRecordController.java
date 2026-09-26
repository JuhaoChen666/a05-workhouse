package com.example.springbootbackend.Controller;

import com.example.springbootbackend.entity.User;
import com.example.springbootbackend.exception.ServiceException;
import com.example.springbootbackend.utils.PermissionUtil;
import com.example.springbootbackend.utils.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/interview-record")
public class InterviewRecordController {
    @Autowired
    private JdbcTemplate jdbcTemplate;

    @GetMapping
    public Result list(@RequestParam(defaultValue = "1") int page,
                       @RequestParam(defaultValue = "10") int pageSize) {
        User user = currentUser();
        int safePage = Math.max(1, page);
        int safePageSize = Math.max(1, Math.min(pageSize, 100));
        int offset = (safePage - 1) * safePageSize;
        Long total = jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM interview_records WHERE user_id = ?",
                Long.class,
                user.getUserID()
        );
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT id, position_id AS positionId, position_name AS positionName, started_at AS startedAt, "
                        + "ended_at AS endedAt, total_score AS totalScore FROM interview_records "
                        + "WHERE user_id = ? ORDER BY started_at DESC LIMIT ? OFFSET ?",
                user.getUserID(), safePageSize, offset
        );
        Map<String, Object> data = new HashMap<>();
        data.put("list", rows);
        data.put("total", total == null ? 0 : total);
        return Result.success(data);
    }

    @GetMapping("/stats")
    public Result stats() {
        User user = currentUser();
        Map<String, Object> row = jdbcTemplate.queryForMap(
                "SELECT COUNT(*) AS totalCount, SUM(CASE WHEN ended_at IS NOT NULL THEN 1 ELSE 0 END) AS finishedCount, "
                        + "AVG(total_score) AS avgScore, MAX(started_at) AS lastAt FROM interview_records WHERE user_id = ?",
                user.getUserID()
        );
        return Result.success(row);
    }

    @GetMapping("/recent-scores")
    public Result recentScores(@RequestParam(defaultValue = "6") int limit) {
        User user = currentUser();
        int safeLimit = Math.max(1, Math.min(limit, 20));
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT id AS interviewRecordId, position_name AS positionName, started_at AS startedAt, total_score AS totalScore "
                        + "FROM interview_records WHERE user_id = ? AND total_score IS NOT NULL "
                        + "ORDER BY started_at DESC LIMIT ?",
                user.getUserID(), safeLimit
        );
        return Result.success(rows);
    }

    @GetMapping("/{id}")
    public Result detail(@PathVariable long id) {
        User user = currentUser();
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT id, position_id AS positionId, position_name AS positionName, started_at AS startedAt, "
                        + "ended_at AS endedAt, total_score AS totalScore FROM interview_records WHERE id = ? AND user_id = ?",
                id, user.getUserID()
        );
        return rows.isEmpty() ? Result.resourceNotExist() : Result.success(rows.get(0));
    }

    @PatchMapping("/{id}/end")
    public Result end(@PathVariable long id) {
        User user = currentUser();
        int rows = jdbcTemplate.update(
                "UPDATE interview_records SET ended_at = COALESCE(ended_at, NOW()) WHERE id = ? AND user_id = ?",
                id, user.getUserID()
        );
        return rows == 0 ? Result.resourceNotExist() : detail(id);
    }

    private User currentUser() {
        try {
            return PermissionUtil.getCurrentUser();
        } catch (ServiceException e) {
            throw e;
        }
    }
}
