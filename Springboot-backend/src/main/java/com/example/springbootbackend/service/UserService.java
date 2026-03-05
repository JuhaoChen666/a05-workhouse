package com.example.springbootbackend.service;

import com.example.springbootbackend.entity.User;
import com.example.springbootbackend.exception.ServiceException;
import com.example.springbootbackend.mapper.UserMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

@Service
public class UserService {
    @Autowired
    private UserMapper userMapper;
    @Autowired
    private BCryptPasswordEncoder PasswordEncoder;
    //根据用户名查找用户
    public User findByUsername(String username){
        return userMapper.FindByUsername(username);
    }
    //根据用户ID查找用户
    public User findByUserID(int userID){
        return userMapper.FindByUserID(userID);
    }


    public User login(User user) {
        User dbuser=findByUsername(user.getUsername());
        if(dbuser==null){
             throw new ServiceException("用户不存在");
        }
        if(user.getPassword()==null) {
            throw new ServiceException("密码不能为空");
        }
        if(!PasswordEncoder.matches(user.getPassword(),dbuser.getPassword())){
            throw new ServiceException("用户名或密码错误");
        }
        return dbuser;
    }

    public int register(User user) {
        if (user.getPassword()==null||user.getConfirmPassword()==null||
                user.getUsername()==null||user.getUsername().isEmpty()||
                user.getConfirmPassword().isEmpty()||user.getPassword().isEmpty()){
            throw new ServiceException("用户名或密码不能为空");
        }
        User dbuser=findByUsername(user.getUsername());
        if(dbuser!=null){
            throw new ServiceException("用户名已存在");
        }
        else if (!user.getConfirmPassword().equals(user.getPassword())) {
            throw new ServiceException("两次密码不一致");
        }
        String encryptedPwd = PasswordEncoder.encode(user.getPassword()); // [!code focus]
        user.setPassword(encryptedPwd);
        user.setAvatar("D:/a05-workhouse/Springboot-backend/src/main/resources/Assets/avatar_default.png");
        user.setRole_id(1);
        return userMapper.insertUser(user);
    }
    public int updatePassword(String username, String password, String confirmPassword) {
        if(password==null||confirmPassword==null||
                password.isEmpty()||confirmPassword.isEmpty()){
            throw new ServiceException("密码不能为空");
        }
        if (!confirmPassword.equals(password)) {
            throw new ServiceException("两次密码不一致");
        }
        String encryptedPwd = PasswordEncoder.encode(password); // [!code focus]
        userMapper.updatePassword(username, encryptedPwd);
        return 1;
    }
}
