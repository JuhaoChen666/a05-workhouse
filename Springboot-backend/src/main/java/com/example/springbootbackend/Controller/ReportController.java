package com.example.springbootbackend.Controller;

import com.example.springbootbackend.entity.User;
import com.example.springbootbackend.utils.PermissionUtil;
import com.example.springbootbackend.utils.Result;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/report")
public class ReportController {
    @Autowired
    private JdbcTemplate jdbcTemplate;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @GetMapping
    public Result getByRecord(@RequestParam long interviewRecordId) {
        User user = PermissionUtil.getCurrentUser();
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT r.id, r.interview_record_id AS interviewRecordId, r.content_json AS content "
                        + "FROM interview_reports r JOIN interview_records ir ON ir.id = r.interview_record_id "
                        + "WHERE r.interview_record_id = ? AND ir.user_id = ?",
                interviewRecordId, user.getUserID()
        );
        if (rows.isEmpty()) return Result.resourceNotExist();
        Map<String, Object> row = new HashMap<>(rows.get(0));
        Object content = row.get("content");
        if (content != null) {
            try {
                row.put("content", objectMapper.readValue(String.valueOf(content), new TypeReference<Map<String, Object>>() {}));
            } catch (Exception ignored) {
                row.put("content", Map.of());
            }
        }
        return Result.success(row);
    }

    @PostMapping
    public Result upsert(@RequestBody Map<String, Object> body) {
        PermissionUtil.getCurrentUser();
        Number recordId = (Number) body.get("interviewRecordId");
        Object content = body.get("content");
        if (recordId == null || content == null) return Result.requestParamError();
        try {
            String json = objectMapper.writeValueAsString(content);
            jdbcTemplate.update(
                    "INSERT INTO interview_reports(interview_record_id, content_json) VALUES (?, ?) "
                            + "ON DUPLICATE KEY UPDATE content_json = VALUES(content_json), updated_at = NOW()",
                    recordId.longValue(), json
            );
            return getByRecord(recordId.longValue());
        } catch (Exception e) {
            return Result.error("保存报告失败：" + e.getMessage());
        }
    }
}
