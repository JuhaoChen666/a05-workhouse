package com.example.springbootbackend.mapper;

import org.apache.ibatis.annotations.*;
import com.example.springbootbackend.entity.User;
import java.util.List;
import java.util.Map;

@Mapper
public interface UserMapper {
    @Select("select id as userID, username , password, email, avatar, role_id from user where username = #{name}")
    User FindByUsername(String name);//根据用户名查找用户
    @Select("select id as userID, username , password, email, avatar, role_id from user where id = #{userID}")
    User FindByUserID(int userID);//根据用户 ID 查找用户
    
    // 根据用户名查找用户（排除指定 ID 的用户，用于更新时检查重复）
    @Select("select id as userID, username , password, email, avatar, role_id from user where username = #{username} and id != #{excludeId}")
    User findByUsernameExcludeId(@Param("username") String username, @Param("excludeId") int excludeId);
    
    @Update("UPDATE user SET password=#{password} WHERE username = #{username}")
    void updatePassword(@Param("username") String name,
                        @Param("password") String newPassword);//根据用户名更新密码

    @Insert("INSERT INTO user(id,username,password,email,avatar,role_id) values (#{userID},#{username},#{password},#{email},#{avatar},#{role_id})")
    int insertUser(User user);//根据用户名注册
    
    // 分页查询用户列表
    @Select("SELECT u.id, u.username, u.email, u.avatar, u.role_id, r.name as role_name " +
            "FROM user u LEFT JOIN role r ON u.role_id = r.id " +
            "ORDER BY u.id DESC LIMIT #{offset}, #{pageSize}")
    List<Map<String, Object>> findUserPage(@Param("offset") int offset, @Param("pageSize") int pageSize);
    
    // 查询用户总数
    @Select("SELECT COUNT(*) FROM user")
    long countUsers();
    
    // 根据 ID 删除用户
    @Delete("DELETE FROM user WHERE id = #{id}")
    int deleteById(@Param("id") int id);
    
    // 更新用户信息
    @Update("<script>" +
            "UPDATE user " +
            "<set>" +
            "  <if test='username != null and username != \"\"'>username = #{username},</if>" +
            "  <if test='email != null'>email = #{email},</if>" +
            "  <if test='roleId != null'>role_id = #{roleId},</if>" +
            "  <if test='avatar != null'>avatar = #{avatar},</if>" +
            "</set>" +
            "WHERE id = #{id}" +
            "</script>")
    int updateUser(User user);
}
