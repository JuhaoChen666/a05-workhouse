package com.example.springbootbackend.service;

import com.example.springbootbackend.entity.User;
import com.example.springbootbackend.exception.ServiceException;
import com.example.springbootbackend.mapper.UserMapper;
import com.example.springbootbackend.utils.AvatarUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
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
        // 存储相对路径而不是绝对路径来保护数据隐私和方便项目迁移
        user.setAvatar(AvatarUtil.getAvatarUrl("avatar_default.webp"));
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
    
    /**
     * 上传用户头像
     * @param userId 用户 ID
     * @param file 上传的文件
     * @return 新头像的访问 URL
     */
    public String uploadAvatar(int userId, MultipartFile file) {
        // 1. 检查用户是否存在
        User user = findByUserID(userId);
        if (user == null) {
            throw new ServiceException("用户不存在");
        }
        
        // 2. 验证文件是否为空
        if (file == null || file.isEmpty()) {
            throw new ServiceException("上传文件不能为空");
        }
        
        // 3. 验证文件格式
        String originalFilename = file.getOriginalFilename();
        if (!AvatarUtil.isAllowedFormat(originalFilename)) {
            throw new ServiceException("不支持的图片格式，仅支持：jpg、jpeg、png、gif、bmp");
        }
        
        try {
            // 4. 读取上传的图片
            BufferedImage image = AvatarUtil.readImage(file.getInputStream());
            if (image == null) {
                throw new ServiceException("图片文件损坏或格式不正确");
            }
            
            // 5. 生成唯一文件名
            String newFilename = AvatarUtil.generateUniqueFilename(userId);
            System.out.println("[头像上传] 生成新文件名: " + newFilename);
            
            // 6. 转换并保存为 WebP 格式（必须保证新图片真正转换且保存成功，才可以开始下一步的删除和入库）
            String savedPath = AvatarUtil.convertAndSave(image, newFilename);
            System.out.println("[头像上传] 新头像保存路径: " + savedPath);

            // 7. 删除旧头像（如果有旧头像且并非默认头像，则删除它的文件实体）
            String oldAvatar = user.getAvatar();
            System.out.println("[头像上传] 旧头像路径: " + oldAvatar);
            if (oldAvatar != null && !oldAvatar.isEmpty()) {
                boolean isDefault = AvatarUtil.isDefaultAvatar(oldAvatar);
                System.out.println("[头像上传] 是否为默认头像: " + isDefault);
                if (!isDefault) {
                    AvatarUtil.deleteOldAvatar(oldAvatar);
                    System.out.println("[头像上传] 已删除旧头像");
                } else {
                    System.out.println("[头像上传] 默认头像，跳过删除");
                }
            }
            
            // 8. 获取新头像的 URL（为了数据安全，直接将该相对路径存放入库）
            String avatarUrl = AvatarUtil.getAvatarUrl(newFilename);
            System.out.println("[头像上传] 数据库存储且将返回的 URL: " + avatarUrl);
            
            // 9. 更新数据库
            int updateCount = userMapper.updateAvatar(userId, avatarUrl);
            System.out.println("[头像上传] 数据库更新结果: " + updateCount + " 行受影响");
            
            if (updateCount == 0) {
                throw new ServiceException("数据库更新失败");
            }
            
            // 10. 返回头像 URL
            return avatarUrl;
            
        } catch (IOException e) {
            System.err.println("[头像上传] IO异常: " + e.getMessage());
            e.printStackTrace();
            throw new ServiceException("头像上传失败：" + e.getMessage());
        }
    }


    //根据ID获取用户头像
    public String getAvatarById(int userId) {
        return userMapper.getAvatarById(userId);
    }
}
