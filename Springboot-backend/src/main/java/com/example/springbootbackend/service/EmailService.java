package com.example.springbootbackend.service;

import com.example.springbootbackend.exception.ServiceException;
import com.example.springbootbackend.utils.RedisUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;

import java.util.concurrent.TimeUnit;

@Service
public class EmailService {

    @Autowired
    private RedisUtils redisUtils;

    @Autowired
    private JavaMailSender mailSender;

    @Value("${spring.mail.username}")
    private String fromEmail;

    // 发送验证码并存入Redis
    public void sendCode(String email) {
        if (email == null || email.isEmpty()) {
            throw new ServiceException("邮箱未绑定");
        }
        // 生成6位随机验证码
        String code = String.format("%06d", (int)(Math.random() * 1000000));

        // 存入Redis，5分钟过期
        redisUtils.set("captcha:" + email, code, 5, TimeUnit.MINUTES);

        // 发送邮件
        SimpleMailMessage message = new SimpleMailMessage();
        message.setFrom(fromEmail);
        message.setTo(email);
        message.setSubject("密码重置验证码");
        message.setText("您的验证码是：" + code + "，5分钟内有效，请勿泄露。");
        mailSender.send(message);
    }

    // 校验验证码
    public void verifyCode(String email, String inputCode) {
        String cachedCode = redisUtils.get("captcha:" + email);
        if (inputCode == null || inputCode.isEmpty()) {
            throw new ServiceException("验证码不能为空");
        } else if (cachedCode == null) {
            throw new ServiceException("验证码已过期或未发送，请重新获取");
        } else if (!cachedCode.equals(inputCode)) {
            throw new ServiceException("验证码错误");
        }else{
            redisUtils.delete("captcha:" + email); // 验证通过后立即删除，防止重复使用

        }
    }
}