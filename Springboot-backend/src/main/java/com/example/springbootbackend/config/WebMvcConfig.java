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
        String avatarDir = AvatarUtil.getAvatarDir();
        // 确保路径以 / 结尾
        if (!avatarDir.endsWith("/")) {
            avatarDir += "/";
        }

        registry.addResourceHandler("/assets/**")
                .addResourceLocations("file:" + avatarDir);
    }
}
