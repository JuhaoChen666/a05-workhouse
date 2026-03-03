package com.example.springbootbackend.utils;

import com.example.coursesystem.entity.User;
import com.example.coursesystem.exception.ServiceException;
import com.example.coursesystem.service.UserService;
import io.jsonwebtoken.Claims;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

public class JwtAuthenticationFilter extends OncePerRequestFilter {
    @Autowired
    private UserService userService;
    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        // 1. 从请求头获取Authorization
        String authHeader = request.getHeader("Authorization");

        // 2. 验证Authorization头格式
        if (!StringUtils.hasText(authHeader) || !authHeader.startsWith("Bearer ")) {
            chain.doFilter(request, response); // 放行到后续过滤器
            return;
        }

        // 3. 提取并验证Token
        try {
            String token = authHeader.substring(7); // 去除"Bearer "前缀
            Claims claims = JwtUtils.getClaimsbyToken(token); // 调用工具类解析

            // 4. 从claims中获取用户名
            String username = claims.getSubject();
            if (!StringUtils.hasText(username)) {
                throw new ServiceException("Token中未包含有效用户信息");
            }

            // 5. 从数据库加载用户详细信息
            User user = userService.findByUsername(username);
            if (user == null) {
                throw new ServiceException("用户不存在或已被禁用");
            }

            // 6. 创建认证对象并注入安全上下文
            UsernamePasswordAuthenticationToken authentication =
                    new UsernamePasswordAuthenticationToken(user, null, user.getAuthorities());
            SecurityContextHolder.getContext().setAuthentication(authentication);

            // 7. 继续过滤器链执行
            chain.doFilter(request, response);

        } catch (ServiceException e) {
            // 8. 自定义异常处理
            response.sendError(HttpServletResponse.SC_UNAUTHORIZED, e.getMessage());
        } catch (Exception e) {
            // 9. 其他异常处理
            response.sendError(HttpServletResponse.SC_UNAUTHORIZED, "无效的访问令牌");
        }
    }
}
