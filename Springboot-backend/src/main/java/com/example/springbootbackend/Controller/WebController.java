package com.example.springbootbackend.Controller;

import com.example.coursesystem.entity.User;
import com.example.coursesystem.service.UserService;
import com.example.coursesystem.utils.JwtUtils;
import com.example.coursesystem.utils.Result;
import jakarta.annotation.Resource;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class WebController {
    @Value("${server.port}")
    private int httpsPort;
    @Resource
    UserService userService;
    @GetMapping("/test")
    public String test(){
        return "hello";
    }
    @PostMapping("/setpwd")
    public Result setpwd(@RequestBody User user){
        user=userService.findByUsername(user.getUsername());
        userService.setPassword(user.getUsername(),user.getPassword());
        return Result.success("密码更新成功");
    }
    @PostMapping("/login")
    public Result login(@RequestBody User user, HttpServletRequest request){
        // 添加HTTPS强制验证
        if (!request.isSecure()) {
            // 修改为Result的标准使用方式 ↓
            Result result = Result.error("308", "请使用HTTPS协议访问");
            result.setData(Map.of(
                    "location", "https://localhost:" + httpsPort + "/login"
            ));
            return result;
        }
        user=userService.login(user);
        String token= JwtUtils.generateToken(user.getUsername());
        return Result.success(Map.of(
                "user", user,
                "token", token
        ));
    }
}
