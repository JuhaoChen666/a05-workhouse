package com.example.springbootbackend.Controller;

import com.example.springbootbackend.entity.User;
import com.example.springbootbackend.exception.ServiceException;
import com.example.springbootbackend.service.UserService;
import com.example.springbootbackend.utils.PermissionUtil;
import com.example.springbootbackend.utils.Result;
import jakarta.annotation.Resource;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/users")
public class UserController {
    
    @Resource
    UserService userService;
    
    /**
     * 获取用户列表（分页）- 需要管理员权限
     */
    @GetMapping
    public Result getUserList(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int pageSize) {
        try {
            // 验证管理员权限
            PermissionUtil.requireAdmin();
            
            Map<String, Object> data = userService.getUserPage(page, pageSize);
            return Result.success(data);
        } catch (ServiceException e) {
            if (e.getMessage().equals("需要管理员权限")) {
                return Result.error("403", "需要管理员权限");
            }
            return Result.error("获取用户列表失败：" + e.getMessage());
        } catch (Exception e) {
            return Result.error("获取用户列表失败：" + e.getMessage());
        }
    }
    
    /**
     * 获取用户详情 - 需要管理员权限
     */
    @GetMapping("/{id}")
    public Result getUserDetail(@PathVariable int id) {
        try {
            // 验证管理员权限
            PermissionUtil.requireAdmin();
            
            User user = userService.findByUserID(id);
            if (user == null) {
                return Result.userNotExist();
            }
            
            Map<String, Object> userData = Map.of(
                "id", user.getUserID(),
                "username", user.getUsername(),
                "email", user.getEmail() != null ? user.getEmail() : "",
                "roleId", user.getRole_id(),
                "avatar", user.getAvatar() != null ? user.getAvatar() : ""
            );
            
            return Result.success(userData);
        } catch (ServiceException e) {
            if (e.getMessage().equals("需要管理员权限")) {
                return Result.noPermission();
            }
            return Result.error("获取用户详情失败：" + e.getMessage());
        } catch (Exception e) {
            return Result.error("获取用户详情失败：" + e.getMessage());
        }
    }
    
    /**
     * 创建用户 - 需要管理员权限
     */
    @PostMapping
    public Result createUser(@RequestBody User user) {
        try {
            // 验证管理员权限
            PermissionUtil.requireAdmin();
            
            // 参数校验
            if (user.getUsername() == null || user.getUsername().isEmpty()) {
                return Result.error("用户名不能为空");
            }
            if (user.getPassword() == null || user.getPassword().isEmpty()) {
                return Result.error("密码不能为空");
            }
            
            // 检查用户名是否已存在
            User existUser = userService.findByUsername(user.getUsername());
            if (existUser != null) {
                return Result.usernameExist();
            }
            
            // 设置默认角色为普通用户（如果未指定）
            if (user.getRole_id() == null) {
                user.setRole_id(1);
            }
            
            // 设置确认密码
            user.setConfirmPassword(user.getPassword());
            
            userService.register(user);
            
            return Result.success("创建用户成功");
        } catch (ServiceException e) {
            if (e.getMessage().equals("需要管理员权限")) {
                return Result.noPermission();
            } else if (e.getMessage().equals("用户名已存在")) {
                return Result.usernameExist();
            } else if (e.getMessage().equals("两次密码不一致")) {
                return Result.passwordNotMatch();
            } else if (e.getMessage().equals("用户名或密码不能为空")) {
                return Result.usernamePasswordEmpty();
            }
            return Result.error("创建用户失败：" + e.getMessage());
        } catch (Exception e) {
            return Result.error("创建用户失败：" + e.getMessage());
        }
    }
    
    /**
     * 更新用户信息 - 需要管理员权限
     */
    @PutMapping("/{id}")
    public Result updateUser(@PathVariable int id, @RequestBody User user) {
        try {
            // 验证管理员权限
            PermissionUtil.requireAdmin();
            
            // 检查用户是否存在
            User existUser = userService.findByUserID(id);
            if (existUser == null) {
                return Result.userNotExist();
            }
            
            // 如果要修改用户名，检查新用户名是否已存在（排除自己）
            if (user.getUsername() != null && !user.getUsername().isEmpty() 
                && !user.getUsername().equals(existUser.getUsername())) {
                // ✅ 根据 ID 排除自己，查找是否有其他用户使用了这个用户名
                User duplicateUser = userService.findByUsernameExcludeId(user.getUsername(), id);
                if (duplicateUser != null) {
                    return Result.usernameExist();
                }
            }
            
            // 设置用户 ID
            user.setUserID(id);
            
            // 不允许修改头像（忽略 avatar 字段）
            user.setAvatar(null);
            
            // 调用 Service 层更新
            userService.updateUser(user);
            
            return Result.success("更新用户成功");
        } catch (ServiceException e) {
            if (e.getMessage().equals("需要管理员权限")) {
                return Result.noPermission();
            }
            return Result.error("更新用户失败：" + e.getMessage());
        } catch (Exception e) {
            // 打印详细异常信息，方便调试
            e.printStackTrace();
            return Result.error("更新用户失败：" + e.getMessage());
        }
    }
    
    /**
     * 删除用户 - 需要管理员权限
     */
    @DeleteMapping("/{id}")
    public Result deleteUser(@PathVariable int id) {
        try {
            // 验证管理员权限
            PermissionUtil.requireAdmin();
            
            // 检查用户是否存在
            User existUser = userService.findByUserID(id);
            if (existUser == null) {
                return Result.userNotExist();
            }
            
            // 不允许删除自己
            User currentUser = PermissionUtil.getCurrentUser();
            if (currentUser.getUserID().equals(id)) {
                return Result.error("不能删除自己的账号");
            }
            
            userService.deleteUser(id);
            
            return Result.success("删除用户成功");
        } catch (ServiceException e) {
            if (e.getMessage().equals("需要管理员权限")) {
                return Result.noPermission();
            }
            return Result.error("删除用户失败：" + e.getMessage());
        } catch (Exception e) {
            return Result.error("删除用户失败：" + e.getMessage());
        }
    }
}
