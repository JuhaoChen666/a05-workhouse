package com.example.springbootbackend.config;

import com.example.springbootbackend.utils.AvatarUtil;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Web MVC 配置
 * 配置静态资源访问路径
 */
@Configuration
public class WebMvcConfig implements WebMvcConfigurer {
    
    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        // 配置头像资源访问路径
        // 访问 /assets/** 时，映射到本地的 Assets 目录
        registry.addResourceHandler("/assets/**")
                .addResourceLocations("file:" + AvatarUtil.getAvatarDir());
    }
}
