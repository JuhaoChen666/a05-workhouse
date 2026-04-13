package com.example.springbootbackend.Controller;

import com.example.springbootbackend.exception.ServiceException;
import com.example.springbootbackend.service.InterviewSessionService;
import com.example.springbootbackend.utils.PermissionUtil;
import com.example.springbootbackend.utils.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

@RestController
@RequestMapping("/admin/sessions")
public class InterviewSessionAdminController {
    
    @Autowired
    private InterviewSessionService interviewSessionService;
    
    /**
     * 分页查询面试会话(支持按user_id查询,支持排序)
     * 需要管理员权限
     */
    @GetMapping("/page")
    public Result getSessionsByPage(
            @RequestParam(required = false) Integer userId,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int pageSize,
            @RequestParam(defaultValue = "asc") String order,
            @RequestParam(required = false) String sortBy) {
        try {
            // 验证管理员权限
            PermissionUtil.requireAdmin();
            
            Map<String, Object> result = interviewSessionService.getSessionsByPage(userId, page, pageSize, order, sortBy);
            return Result.success(result);
        } catch (ServiceException e) {
            if (e.getMessage().equals("需要管理员权限")) {
                return Result.noPermission();
            }
            return Result.error("查询会话列表失败：" + e.getMessage());
        } catch (Exception e) {
            return Result.error("查询会话列表失败：" + e.getMessage());
        }
    }
    
    /**
     * 删除面试会话(根据session_id)
     * 需要管理员权限
     */
    @DeleteMapping("/{sessionId}")
    public Result deleteSession(@PathVariable String sessionId) {
        try {
            // 验证管理员权限
            PermissionUtil.requireAdmin();
            
            int rows = interviewSessionService.deleteSessionById(sessionId);
            if (rows > 0) {
                return Result.success("删除会话成功");
            } else {
                return Result.error("会话不存在或删除失败");
            }
        } catch (ServiceException e) {
            if (e.getMessage().equals("需要管理员权限")) {
                return Result.noPermission();
            }
            return Result.error("删除会话失败：" + e.getMessage());
        } catch (Exception e) {
            return Result.error("删除会话失败：" + e.getMessage());
        }
    }
}
