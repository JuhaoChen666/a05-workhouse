package com.example.springbootbackend.config;

import com.example.springbootbackend.utils.JwtAuthenticationFilter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public BCryptPasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
    
    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
                .addFilterBefore(jwtAuthenticationFilter(), UsernamePasswordAuthenticationFilter.class)
                .authorizeHttpRequests(auth -> auth
                        // 公开接口
                        .requestMatchers("/auth/login", "/auth/register", "/auth/send-code", "/auth/verify-code").permitAll()
                        .requestMatchers("/test", "/test-redis", "/roles").permitAll()
                        .requestMatchers("/jobs/**").permitAll()
                        .requestMatchers("/positions/**").permitAll()
                        // 静态资源
                        .requestMatchers("/admin/**", "/static/**", "/assets/**").permitAll()
                        // 用户管理接口 - 需要认证（后续可在 Controller 中检查角色）
                        .requestMatchers("/users/**").authenticated()
                        // 其他所有请求需要认证
                        .anyRequest().authenticated()
                )
                .csrf(csrf -> csrf.disable());
        return http.build();
    }
    
    @Bean
    public JwtAuthenticationFilter jwtAuthenticationFilter() {
        return new JwtAuthenticationFilter();
    }
}