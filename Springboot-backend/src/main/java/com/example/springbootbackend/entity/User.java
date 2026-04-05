package com.example.springbootbackend.entity;

import lombok.Data;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

@Data
public class User implements UserDetails {
        private Integer userID;
        private String username;
        private String password;
        private String email;
        private String avatar;
        private Integer role_id;
        private String confirmPassword;

        // 为了兼容 MyBatis 的驼峰命名和简化属性名，添加这些方法
        public Integer getId() {
            return userID;
        }

        public void setId(Integer id) {
            this.userID = id;
        }
        
        public Integer getRoleId() {
            return role_id;
        }

        public void setRoleId(Integer roleId) {
            this.role_id = roleId;
        }



    @Override
    public Collection<? extends GrantedAuthority> getAuthorities() {
        List<GrantedAuthority> authorities = new ArrayList<>();
        if (role_id == 2) {
            authorities.add(new SimpleGrantedAuthority("ROLE_ADMIN"));
        } else {
            authorities.add(new SimpleGrantedAuthority("ROLE_USER"));
        }
        return authorities;
    }

    @Override
    public String getUsername() {
        return username;
    }

}
