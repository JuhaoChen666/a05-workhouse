package com.example.springbootbackend.utils;

import com.example.springbootbackend.entity.User;
import com.example.springbootbackend.exception.ServiceException;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;

import javax.crypto.SecretKey;
import java.util.Date;

public class JwtUtils {
    // 2小时
    private static long expire = 7200;
    // 密钥
    private static String secret = "CJHNBCJHNBCJHNBCJHNBCJHNBCJHNBCJHNB";

    /**
     * 生成Token
     * @param user 用户信息
     * @return JWT Token
     */
    public static String generateToken(User user) {
        Date now = new Date();
        Date expireDate = new Date(now.getTime() + expire * 1000);
        SecretKey key = Keys.hmacShaKeyFor(secret.getBytes());
        return Jwts.builder()
                .header().add("typ", "JWT").and()
                .claim("id", user.getUserID())
                .claim("username", user.getUsername())
                .claim("roleId", user.getRole_id())
                .issuedAt(now)
                .expiration(expireDate)
                .signWith(key)
                .compact();
    }

    /**
     * 解析Token
     * @param token JWT Token
     * @return Claims
     */
    public static Claims getClaimsbyToken(String token) {
        try {
            SecretKey key = Keys.hmacShaKeyFor(secret.getBytes());
            return Jwts.parser()
                    .verifyWith(key)
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();
        } catch (Exception e) {
            throw new ServiceException("Token解析失败: " + e.getMessage());
        }
    }
}
