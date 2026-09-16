package com.example.springbootbackend.Controller;

import com.example.springbootbackend.service.AvatarAuthService;
import com.example.springbootbackend.utils.PermissionUtil;
import com.example.springbootbackend.utils.Result;
import jakarta.annotation.Resource;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/auth/avatar")
public class AvatarController {

    @Resource
    private AvatarAuthService avatarAuthService;

    /**
     * 获取虚拟人鉴权信息
     * 只有登录用户可以获取签名
     */
    @GetMapping("/auth")
    public Result getAvatarAuth() {
        try {
            // 验证用户是否登录
            PermissionUtil.getCurrentUser();

            String signedUrl = avatarAuthService.getSignedUrl();
            String appId = avatarAuthService.getAppId();
            String sceneId = avatarAuthService.getSceneId();

            Map<String, Object> data = new HashMap<>();
            data.put("signedUrl", signedUrl);
            data.put("appId", appId);
            data.put("sceneId", sceneId);
            
            return Result.success(data);
        } catch (Exception e) {
            return Result.error("获取虚拟人鉴权失败：" + e.getMessage());
        }
    }
}
