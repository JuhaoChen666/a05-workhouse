package com.example.springbootbackend.utils;

import com.example.coursesystem.exception.ServiceException;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;

import javax.crypto.SecretKey;
import java.util.Date;

public class JwtUtils {
    //7天
    private static long expire = 604800;
    //密钥
    private static String secret = "CJHNBCJHNBCJHNBCJHNBCJHNBCJHNBCJHNB";

    //token前缀
    public static String generateToken(String username) {
        Date now = new Date();
        Date expireDate = new Date(now.getTime() + expire * 1000);//过期时间
        SecretKey key = Keys.hmacShaKeyFor(secret.getBytes());
        return Jwts.builder()
                .header().add("typ", "JWT").and()
                .subject(username)
                .issuedAt(now)
                .expiration(expireDate)
                .signWith(key)  // 新版签名方式
                .compact();
    }

    //解析Token
    public static Claims getClaimsbyToken(String token) {
        try {
            SecretKey key = Keys.hmacShaKeyFor(secret.getBytes());
            return Jwts.parser()
                    .verifyWith(key)
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();
        } catch (Exception e) { // 添加异常捕获
            throw new ServiceException("Token解析失败: " + e.getMessage());
        }
    }
}
