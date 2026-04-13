package com.example.springbootbackend.Controller;

import com.example.springbootbackend.exception.ServiceException;
import com.example.springbootbackend.service.ResumeService;
import com.example.springbootbackend.utils.PermissionUtil;
import com.example.springbootbackend.utils.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

@RestController
@RequestMapping("/admin/resumes")
public class ResumeAdminController {
    
    @Autowired
    private ResumeService resumeService;
    
    /**
     * 分页查询简历(支持按user_id查询)
     * 需要管理员权限
     */
    @GetMapping("/page")
    public Result getResumesByPage(
            @RequestParam(required = false) Integer userId,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int pageSize) {
        try {
            // 验证管理员权限
            PermissionUtil.requireAdmin();
            
            Map<String, Object> result = resumeService.getResumesByPage(userId, page, pageSize);
            return Result.success(result);
        } catch (ServiceException e) {
            if (e.getMessage().equals("需要管理员权限")) {
                return Result.noPermission();
            }
            return Result.error("查询简历列表失败：" + e.getMessage());
        } catch (Exception e) {
            return Result.error("查询简历列表失败：" + e.getMessage());
        }
    }
    
    /**
     * 删除简历(根据主键id)
     * 需要管理员权限
     */
    @DeleteMapping("/{id}")
    public Result deleteResume(@PathVariable Long id) {
        try {
            // 验证管理员权限
            PermissionUtil.requireAdmin();
            
            int rows = resumeService.deleteResumeById(id);
            if (rows > 0) {
                return Result.success("删除简历成功");
            } else {
                return Result.error("简历不存在或删除失败");
            }
        } catch (ServiceException e) {
            if (e.getMessage().equals("需要管理员权限")) {
                return Result.noPermission();
            }
            return Result.error("删除简历失败：" + e.getMessage());
        } catch (Exception e) {
            return Result.error("删除简历失败：" + e.getMessage());
        }
    }
}
