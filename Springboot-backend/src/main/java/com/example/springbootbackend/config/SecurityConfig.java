package com.example.springbootbackend.config;

import com.example.springbootbackend.utils.JwtAuthenticationFilter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import java.util.Arrays;

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
                .cors(cors -> cors.configurationSource(corsConfigurationSource()))
                .addFilterBefore(jwtAuthenticationFilter(), UsernamePasswordAuthenticationFilter.class)
                .authorizeHttpRequests(auth -> auth
                        // 公开接口
                        .requestMatchers("/auth/login", "/auth/register", "/auth/send-code", "/auth/verify-code").permitAll()
                        .requestMatchers("/test", "/test-redis", "/roles").permitAll()
                        .requestMatchers("/jobs/**").permitAll()
                        .requestMatchers("/positions/**").permitAll()
                        // 调试接口（临时）
                        .requestMatchers("/debug/**").permitAll()
                        // 静态资源
                        .requestMatchers("/static/**", "/assets/**").permitAll()
                        // 管理员接口 - 需要认证（在 Controller 中检查角色）
                        .requestMatchers("/admin/**").authenticated()
                        // 用户管理接口 - 需要认证（后续可在 Controller 中检查角色）
                        .requestMatchers("/users/**").authenticated()
                        // 其他所有请求需要认证
                        .anyRequest().authenticated()
                )
                .csrf(csrf -> csrf.disable());
        return http.build();
    }
    
    @Bean
    public UrlBasedCorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        // 修复：当 allowCredentials=true 时，不能使用 "*" 通配符
        // 使用 setAllowedOrigins 并指定具体域名，或使用 setAllowedOriginPatterns
        configuration.setAllowedOriginPatterns(Arrays.asList("*")); // 使用 patterns 允许所有
        configuration.setAllowedMethods(Arrays.asList("GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"));
        configuration.setAllowedHeaders(Arrays.asList("*"));
        configuration.setExposedHeaders(Arrays.asList("*"));
        // 关键修复：如果要使用 credentials，originPatterns 不能用 "*"
        // 方案1：关闭 credentials（推荐用于 API）
        configuration.setAllowCredentials(false);
        // 方案2：或者使用具体的域名列表（如果需要 credentials）
        // configuration.setAllowCredentials(true);
        // configuration.setAllowedOrigins(Arrays.asList("http://localhost:5173", "http://192.168.1.100:5173"));
        configuration.setMaxAge(3600L); // 预检请求的缓存时间
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }
    
    @Bean
    public JwtAuthenticationFilter jwtAuthenticationFilter() {
        return new JwtAuthenticationFilter();
    }
}