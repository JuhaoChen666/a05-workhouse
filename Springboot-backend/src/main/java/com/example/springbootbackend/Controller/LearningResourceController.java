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
@RequestMapping("/learning-resource")
public class LearningResourceController {
    @Autowired
    private JdbcTemplate jdbcTemplate;

    @GetMapping
    public Result list(@RequestParam(defaultValue = "1") int page,
                       @RequestParam(defaultValue = "10") int pageSize,
                       @RequestParam(required = false, defaultValue = "") String tags) {
        int safePage = Math.max(1, page);
        int safePageSize = Math.max(1, Math.min(pageSize, 100));
        int offset = (safePage - 1) * safePageSize;
        String tag = tags.trim();
        boolean filtered = !tag.isEmpty();
        String where = filtered ? " WHERE tags LIKE ?" : "";
        String select = "SELECT id, title, link, tags FROM learning_resource" + where + " ORDER BY id DESC LIMIT ? OFFSET ?";
        String count = "SELECT COUNT(*) FROM learning_resource" + where;
        Long total;
        List<Map<String, Object>> rows;
        if (filtered) {
            String kw = "%" + tag + "%";
            total = jdbcTemplate.queryForObject(count, Long.class, kw);
            rows = jdbcTemplate.queryForList(select, kw, safePageSize, offset);
        } else {
            total = jdbcTemplate.queryForObject(count, Long.class);
            rows = jdbcTemplate.queryForList(select, safePageSize, offset);
        }
        Map<String, Object> data = new HashMap<>();
        data.put("list", rows);
        data.put("total", total == null ? 0 : total);
        return Result.success(data);
    }

    @PostMapping
    public Result create(@RequestBody Map<String, Object> body) {
        try {
            PermissionUtil.requireAdmin();
            String title = requiredText(body.get("title"));
            String link = requiredText(body.get("link"));
            if (title.isEmpty() || link.isEmpty()) return Result.requestParamError();
            KeyHolder keyHolder = new GeneratedKeyHolder();
            jdbcTemplate.update(connection -> {
                PreparedStatement ps = connection.prepareStatement(
                        "INSERT INTO learning_resource(title, link, tags) VALUES (?, ?, ?)",
                        Statement.RETURN_GENERATED_KEYS
                );
                ps.setString(1, title);
                ps.setString(2, link);
                ps.setString(3, nullableString(body.get("tags")));
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
            String title = requiredText(body.get("title"));
            String link = requiredText(body.get("link"));
            if (title.isEmpty() || link.isEmpty()) return Result.requestParamError();
            int rows = jdbcTemplate.update(
                    "UPDATE learning_resource SET title = ?, link = ?, tags = ? WHERE id = ?",
                    title, link, nullableString(body.get("tags")), id
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
            int rows = jdbcTemplate.update("DELETE FROM learning_resource WHERE id = ?", id);
            return rows == 0 ? Result.resourceNotExist() : Result.success();
        } catch (ServiceException e) {
            return Result.noPermission();
        }
    }

    private Result detail(long id) {
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT id, title, link, tags FROM learning_resource WHERE id = ?",
                id
        );
        return rows.isEmpty() ? Result.resourceNotExist() : Result.success(rows.get(0));
    }

    private String requiredText(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private String nullableString(Object value) {
        String text = requiredText(value);
        return text.isEmpty() ? null : text;
    }
}
