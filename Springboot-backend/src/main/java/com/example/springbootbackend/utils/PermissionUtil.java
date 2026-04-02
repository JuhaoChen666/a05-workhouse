package com.example.springbootbackend.utils;

import com.example.springbootbackend.entity.User;
import com.example.springbootbackend.exception.ServiceException;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;

/**
 * 权限验证工具类
 */
@Component
public class PermissionUtil {
    
    /**
     * 获取当前登录用户
     * @return User 对象
     */
    public static User getCurrentUser() {
        Object principal = SecurityContextHolder.getContext().getAuthentication().getPrincipal();
        if (principal instanceof User) {
            return (User) principal;
        }
        throw new ServiceException("用户未登录");
    }
    
    /**
     * 检查当前用户是否为管理员
     * @return true-是管理员，false-非管理员
     */
    public static boolean isAdmin() {
        try {
            User user = getCurrentUser();
            return user.getRole_id() != null && user.getRole_id() == 2;
        } catch (Exception e) {
            return false;
        }
    }
    
    /**
     * 验证管理员权限，如果不是管理员则抛出异常
     */
    public static void requireAdmin() {
        User user = getCurrentUser();
        if (user.getRole_id() == null || user.getRole_id() != 2) {
            throw new ServiceException("需要管理员权限");
        }
    }
}
