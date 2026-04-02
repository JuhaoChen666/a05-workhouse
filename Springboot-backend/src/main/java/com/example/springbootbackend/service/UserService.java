package com.example.springbootbackend.service;

import com.example.springbootbackend.entity.User;
import com.example.springbootbackend.exception.ServiceException;
import com.example.springbootbackend.mapper.UserMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

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
    //根据用户 ID 查找用户
    public User findByUserID(int userID){
        return userMapper.FindByUserID(userID);
    }
    // 根据用户名查找用户（排除指定 ID，用于更新时检查重复）
    public User findByUsernameExcludeId(String username, int excludeId){
        return userMapper.findByUsernameExcludeId(username, excludeId);
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
        // 基于时间戳自动生成用户 ID
        int generatedId = (int) (System.currentTimeMillis() % Integer.MAX_VALUE);
        user.setUserID(generatedId);
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
    
    // 分页查询用户列表
    public Map<String, Object> getUserPage(int page, int pageSize) {
        int offset = (page - 1) * pageSize;
        List<Map<String, Object>> users = userMapper.findUserPage(offset, pageSize);
        long total = userMapper.countUsers();
        
        // 转换数据格式为前端期望的驼峰命名，并只保留需要的字段
        List<Map<String, Object>> userList = new java.util.ArrayList<>();
        for (Map<String, Object> user : users) {
            Map<String, Object> userData = new HashMap<>();
            // id 转为字符串类型
            userData.put("id", String.valueOf(user.get("id")));
            userData.put("username", user.get("username"));
            userData.put("email", user.get("email") != null ? user.get("email") : "");
            userData.put("roleId", user.get("role_id"));
            userData.put("roleName", user.get("role_name"));
            userList.add(userData);
        }
        
        Map<String, Object> result = new HashMap<>();
        result.put("list", userList);
        result.put("total", total);
        return result;
    }
    
    // 删除用户
    public int deleteUser(int id) {
        return userMapper.deleteById(id);
    }
    
    // 更新用户
    public int updateUser(User user) {
        // 如果修改了密码，需要加密
        if (user.getPassword() != null && !user.getPassword().isEmpty()) {
            String encryptedPwd = PasswordEncoder.encode(user.getPassword());
            user.setPassword(encryptedPwd);
        } else {
            // 密码为空时，设置为 null，MyBatis 不会更新这个字段
            user.setPassword(null);
        }
        return userMapper.updateUser(user);
    }
}
