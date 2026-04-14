package com.example.springbootbackend.Controller;

import com.example.springbootbackend.entity.Positions;
import com.example.springbootbackend.entity.Positions_Info;
import com.example.springbootbackend.exception.ServiceException;
import com.example.springbootbackend.service.PositionsService;
import com.example.springbootbackend.utils.PermissionUtil;
import com.example.springbootbackend.utils.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/admin/positions")
public class AdminPositionsController {
    @Autowired
    private PositionsService positionsService;

    @GetMapping("/page")
    public Result getPositionsByPage(@RequestParam(required = false, defaultValue = "") String name, 
                                    @RequestParam(defaultValue = "1") int page, 
                                    @RequestParam(defaultValue = "10") int pageSize) {
        try {
            // 验证管理员权限（新创建的接口）
            PermissionUtil.requireAdmin();
            Map<String, Object> result = positionsService.getPositionsByPage(name, page, pageSize);
            return Result.success(result);
        } catch (ServiceException e) {
            if (e.getMessage().equals("需要管理员权限")) {
                return Result.noPermission();
            }
            return Result.error(e.getMessage());
        }
    }
    
    @PostMapping
    public Result addPosition(@RequestBody Positions position) {
        try {
            // 验证管理员权限（新创建的接口）
            PermissionUtil.requireAdmin();
            int result = positionsService.addPosition(position);
            if (result > 0) {
                return Result.success(position);
            } else {
                return Result.error("1010","添加岗位失败");
            }
        } catch (ServiceException e) {
            if (e.getMessage().equals("需要管理员权限")) {
                return Result.noPermission();
            }
            return Result.error(e.getMessage());
        }
    }
    
    @PostMapping("/info")
    public Result addPositionInfo(@RequestBody Positions_Info positionInfo) {
        try {
            // 验证管理员权限（新创建的接口）
            PermissionUtil.requireAdmin();
            
            // 检查id是否为空
            if (positionInfo.getId() == 0) {
                return Result.error("1013", "岗位ID不能为空");
            }
            
            int result = positionsService.addPositionInfo(positionInfo);
            if (result > 0) {
                // 构建访问岗位信息的URL
                String url = "http://localhost:8080/positions/" + positionInfo.getId();
                // 返回包含URL和岗位信息的响应
                java.util.Map<String, Object> data = new java.util.HashMap<>();
                data.put("positionInfo", positionInfo);
                data.put("url", url);
                return Result.success(data);
            } else {
                return Result.error("1011","添加岗位信息失败");
            }
        } catch (ServiceException e) {
            if (e.getMessage().equals("需要管理员权限")) {
                return Result.noPermission();
            }
            return Result.error(e.getMessage());
        } catch (Exception e) {
            // 打印详细异常信息，方便调试
            e.printStackTrace();
            return Result.error("添加岗位信息失败：" + e.getMessage());
        }
    }
    
    @PutMapping("/info")
    public Result updatePositionInfo(@RequestBody Positions_Info positionInfo) {
        try {
            // 验证管理员权限（新创建的接口）
            PermissionUtil.requireAdmin();
            int result = positionsService.updatePositionInfo(positionInfo);
            if (result > 0) {
                return Result.success(positionInfo);
            } else {
                return Result.error("1012","更新岗位信息失败");
            }
        } catch (ServiceException e) {
            if (e.getMessage().equals("需要管理员权限")) {
                return Result.noPermission();
            }
            return Result.error(e.getMessage());
        }
    }
    
    @DeleteMapping("/{id}")
    public Result deletePosition(@PathVariable Integer id) {
        try {
            // 验证管理员权限（修改操作）
            PermissionUtil.requireAdmin();
            int result = positionsService.deletePosition(id);
            if (result == 0) {
                return Result.resourceNotExist();
            }
            return Result.success();
        } catch (ServiceException e) {
            if (e.getMessage().equals("需要管理员权限")) {
                return Result.noPermission();
            }
            return Result.error(e.getMessage());
        }
    }
}