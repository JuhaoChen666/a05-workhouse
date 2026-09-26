package com.example.springbootbackend.Controller;

import com.example.springbootbackend.exception.ServiceException;
import com.example.springbootbackend.utils.PermissionUtil;
import com.example.springbootbackend.utils.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.web.bind.annotation.*;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/question-bank")
public class QuestionBankController {
    @Autowired
    private JdbcTemplate jdbcTemplate;

    @GetMapping
    public Result list(@RequestParam(defaultValue = "1") int page,
                       @RequestParam(defaultValue = "10") int pageSize,
                       @RequestParam(required = false) Integer positionId) {
        int safePage = Math.max(1, page);
        int safePageSize = Math.max(1, Math.min(pageSize, 100));
        int offset = (safePage - 1) * safePageSize;
        boolean filtered = positionId != null;
        String where = filtered ? " WHERE q.position_id = ?" : "";
        String select = "SELECT q.id, q.position_id AS positionId, COALESCE(p.name, '') AS positionName, "
                + "q.question, q.answer, q.knowledge_tags AS knowledgeTags "
                + "FROM question_bank q LEFT JOIN positions p ON p.id = q.position_id"
                + where + " ORDER BY q.id DESC LIMIT ? OFFSET ?";
        String count = "SELECT COUNT(*) FROM question_bank q" + where;
        Long total;
        List<Map<String, Object>> rows;
        if (filtered) {
            total = jdbcTemplate.queryForObject(count, Long.class, positionId);
            rows = jdbcTemplate.queryForList(select, positionId, safePageSize, offset);
        } else {
            total = jdbcTemplate.queryForObject(count, Long.class);
            rows = jdbcTemplate.queryForList(select, safePageSize, offset);
        }
        Map<String, Object> data = new HashMap<>();
        data.put("list", rows);
        data.put("total", total == null ? 0 : total);
        return Result.success(data);
    }

    @GetMapping("/{id}")
    public Result detail(@PathVariable long id) {
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT q.id, q.position_id AS positionId, COALESCE(p.name, '') AS positionName, "
                        + "q.question, q.answer, q.knowledge_tags AS knowledgeTags "
                        + "FROM question_bank q LEFT JOIN positions p ON p.id = q.position_id WHERE q.id = ?",
                id
        );
        return rows.isEmpty() ? Result.resourceNotExist() : Result.success(rows.get(0));
    }

    @PostMapping
    public Result create(@RequestBody Map<String, Object> body) {
        try {
            PermissionUtil.requireAdmin();
            Number positionId = (Number) body.get("positionId");
            String question = String.valueOf(body.getOrDefault("question", "")).trim();
            if (positionId == null || question.isEmpty()) {
                return Result.requestParamError();
            }
            String answer = nullableString(body.get("answer"));
            String tags = nullableString(body.get("knowledgeTags"));
            KeyHolder keyHolder = new GeneratedKeyHolder();
            jdbcTemplate.update(connection -> {
                PreparedStatement ps = connection.prepareStatement(
                        "INSERT INTO question_bank(position_id, question, answer, knowledge_tags) VALUES (?, ?, ?, ?)",
                        Statement.RETURN_GENERATED_KEYS
                );
                ps.setInt(1, positionId.intValue());
                ps.setString(2, question);
                ps.setString(3, answer);
                ps.setString(4, tags);
                return ps;
            }, keyHolder);
            Number key = keyHolder.getKey();
            return detail(key == null ? 0 : key.longValue());
        } catch (ServiceException e) {
            return Result.noPermission();
        }
    }

    @PutMapping("/{id}")
    public Result update(@PathVariable long id, @RequestBody Map<String, Object> body) {
        try {
            PermissionUtil.requireAdmin();
            Number positionId = (Number) body.get("positionId");
            String question = String.valueOf(body.getOrDefault("question", "")).trim();
            if (positionId == null || question.isEmpty()) {
                return Result.requestParamError();
            }
            int rows = jdbcTemplate.update(
                    "UPDATE question_bank SET position_id = ?, question = ?, answer = ?, knowledge_tags = ? WHERE id = ?",
                    positionId.intValue(), question, nullableString(body.get("answer")), nullableString(body.get("knowledgeTags")), id
            );
            return rows == 0 ? Result.resourceNotExist() : detail(id);
        } catch (ServiceException e) {
            return Result.noPermission();
        }
    }

    @DeleteMapping("/{id}")
    public Result delete(@PathVariable long id) {
        try {
            PermissionUtil.requireAdmin();
            int rows = jdbcTemplate.update("DELETE FROM question_bank WHERE id = ?", id);
            return rows == 0 ? Result.resourceNotExist() : Result.success();
        } catch (ServiceException e) {
            return Result.noPermission();
        }
    }

    private String nullableString(Object value) {
        if (value == null) return null;
        String text = String.valueOf(value).trim();
        return text.isEmpty() ? null : text;
    }
}
