package com.example.springbootbackend.Controller;

import com.example.springbootbackend.entity.User;
import com.example.springbootbackend.exception.ServiceException;
import com.example.springbootbackend.service.EmailService;
import com.example.springbootbackend.service.UserService;
import com.example.springbootbackend.utils.JwtUtils;
import com.example.springbootbackend.utils.Result;
import com.example.springbootbackend.utils.UserV0;
import jakarta.annotation.Resource;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
public class WebController {
    @Resource
    UserService userService;

    // 测试接口
    @GetMapping("/test")
    public String test(){
        return "hello";
    }
    @Autowired
    private RedisTemplate<String, String> redisTemplate;
    // 测试Redis连接

    @GetMapping("/test-redis")
    public String testRedis() {
        redisTemplate.opsForValue().set("test-key", "hello-redis");
        String value = redisTemplate.opsForValue().get("test-key");
        return "Redis连接成功，取到的值：" + value;
    }


    // 登录接口
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
    // 注册接口
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
    @Autowired
    private EmailService emailService;
    // 发送验证码
    @PostMapping("/auth/send-code")
    public Result sendCode(@RequestBody Map<String, String> body) {
        String username = body.get("username");

        if (username == null || username.isEmpty()) {
            return Result.usernameEmpty();
        }

        // 根据用户名查找用户
        User user = userService.findByUsername(username);
        if (user == null) {
            return Result.userNotExist();
        }

        String email = user.getEmail();
        try {
            emailService.sendCode(email);
            // 只返回邮箱的部分字符，保护隐私，例如：ab****@qq.com
            String maskedEmail = email.replaceAll("(\\w{2})\\w+(@.*)", "$1****$2");
            return Result.success("验证码已发送至：" + maskedEmail);
        } catch (ServiceException e) {
            if (e.getMessage().equals("邮箱未绑定")) {
                return Result.emailNotBound();
            }
            return Result.error(e.getMessage());
        }
    }
    // 校验验证码并重置密码
    @PostMapping("/auth/verify-code")

    public Result verifyCode(@RequestBody Map<String, String> body) {
        String username = body.get("username");

        String code = body.get("code");
        String newpassword=body.get("newpassword");
        String confirmPassword=body.get("confirmPassword");
        String email = userService.findByUsername(username).getEmail();
        try{
            emailService.verifyCode(email, code);
            if (userService.updatePassword(username, newpassword, confirmPassword)==1) {
                return Result.success("密码重置成功");
            }
        }catch (ServiceException e) {
            if (e.getMessage().equals("验证码错误")){
                return Result.captchaError();
            } else if (e.getMessage().equals("验证码不能为空")) {
                return Result.captchaEmpty();
            }else if (e.getMessage().equals("密码不能为空")){
                return Result.passwordEmpty();
            }
            else if (e.getMessage().equals("两次密码不一致")){
                return Result.passwordNotMatch();
            }
            return Result.error(e.getMessage());
        }
        return Result.error("密码重置失败");
    }
}


