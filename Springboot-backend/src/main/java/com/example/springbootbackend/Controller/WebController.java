package com.example.springbootbackend.Controller;

import com.example.springbootbackend.entity.User;
import com.example.springbootbackend.exception.ServiceException;
import com.example.springbootbackend.service.UserService;
import com.example.springbootbackend.utils.JwtUtils;
import com.example.springbootbackend.utils.Result;
import com.example.springbootbackend.utils.UserV0;
import jakarta.annotation.Resource;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;

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
        user=userService.findByUserID(user.getUserID());
        userService.setPassword(user.getUserID(),user.getPassword());
        return Result.success("密码更新成功");
    }
    @PostMapping("/auth/login")
    public Result login(@RequestBody User user){

        try {
            user=userService.login(user);
            String token= JwtUtils.generateToken(user);
            UserV0 userv0=new UserV0();
            userv0.setId(user.getUserID());
            userv0.setUsername(user.getUsername());
            userv0.setRoleID(user.getRole_id());
            if (user.getRole_id()==1){
                userv0.setRoleName("普通用户");
            }else if (user.getRole_id()==2){
                userv0.setRoleName("管理员");
            }
            return Result.success(Map.of(
                    "token", token,
                    "user", userv0

            ));

        } catch (ServiceException e) {
            if (e.getMessage().equals("用户不存在")) {
                return Result.userNotExist();
            } else if (e.getMessage().equals("用户名或密码错误")) {
                return Result.usernamePasswordError();
            } else if (e.getMessage().equals("用户名和密码不能为空")) {
                return Result.usernamePasswordEmpty();
            }
            return Result.error( e.getMessage());
        }

    }
    @PostMapping("/auth/register")
    public Result register(@RequestBody User user){
        try {
            userService.register(user);

            return Result.success("注册成功");
        } catch (ServiceException e) {
            if (e.getMessage().equals("用户名已存在")) {
                return Result.usernameExist();
            } else if (e.getMessage().equals("两次密码不一致")) {
                return Result.passwordNotMatch();
            }else if (e.getMessage().equals("用户名或密码不能为空")) {
                return Result.usernamePasswordEmpty();
        }
                return Result.error( e.getMessage());
    }
}
}


