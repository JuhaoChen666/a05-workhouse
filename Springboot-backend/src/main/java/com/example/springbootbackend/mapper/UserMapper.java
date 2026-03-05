package com.example.springbootbackend.mapper;

import org.apache.ibatis.annotations.*;
import com.example.springbootbackend.entity.User;

@Mapper
public interface UserMapper {
    @Select("select id as userID, username , password, email, avatar, role_id from user where username = #{name}")
    User FindByUsername(String name);//根据用户名查找用户
    @Select("select id as userID, username , password, email, avatar, role_id from user where id = #{userID}")
    User FindByUserID(int userID);//根据用户ID查找用户
    @Update("UPDATE user SET password=#{password} WHERE username = #{username}")
    void updatePassword(@Param("username") String name,
                        @Param("password") String newPassword);//根据用户名更新密码

    @Insert("INSERT INTO user(id,username,password,email,avatar,role_id) values (#{userID},#{username},#{password},#{email},#{avatar},#{role_id})")
    int insertUser(User user);//根据用户名注册

}
