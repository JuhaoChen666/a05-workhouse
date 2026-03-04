package com.example.springbootbackend.utils;

import com.example.springbootbackend.entity.User;
import com.example.springbootbackend.exception.ServiceException;
import io.jsonwebtoken.Claims;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

public class JwtAuthenticationFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        // 1. 从请求头获取Authorization
        String authHeader = request.getHeader("Authorization");

        // 2. 验证Authorization头格式
        if (!StringUtils.hasText(authHeader) || !authHeader.startsWith("Bearer ")) {
            chain.doFilter(request, response);
            return;
        }

        // 3. 提取并验证Token
        try {
            String token = authHeader.substring(7);
            Claims claims = JwtUtils.getClaimsbyToken(token);

            // 4. 从claims中获取用户信息
            Integer id = claims.get("id", Integer.class);
            String username = claims.get("username", String.class);
            Integer roleId = claims.get("roleId", Integer.class);

            if (id == null || !StringUtils.hasText(username) || roleId == null) {
                throw new ServiceException("Token中未包含有效用户信息");
            }

            // 5. 构建用户对象
            User user = new User();
            user.setUserID(id);
            user.setUsername(username);
            user.setRole_id(roleId);

            // 6. 创建认证对象并注入安全上下文
            UsernamePasswordAuthenticationToken authentication =
                    new UsernamePasswordAuthenticationToken(user, null, user.getAuthorities());
            SecurityContextHolder.getContext().setAuthentication(authentication);

            // 7. 继续过滤器链执行
            chain.doFilter(request, response);

        } catch (ServiceException e) {
            response.sendError(HttpServletResponse.SC_UNAUTHORIZED, e.getMessage());
        } catch (Exception e) {
            response.sendError(HttpServletResponse.SC_UNAUTHORIZED, "无效的访问令牌");
        }
    }
}
