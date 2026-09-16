package com.example.springbootbackend.utils;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.Arrays;
import java.util.List;
import java.util.UUID;

/**
 * 头像处理工具类
 * 支持图片格式验证、WebP 转换、文件保存等功能
 */
public class AvatarUtil {
    
    // 允许上传的图片格式
    private static final List<String> ALLOWED_EXTENSIONS = Arrays.asList("jpg", "jpeg", "png", "gif", "bmp");
    
    // 头像存储目录
    private static final String AVATAR_DIR = System.getProperty("os.name").toLowerCase().contains("win")
            ? "D:/a05-workhouse/Springboot-backend/src/main/resources/Assets/"
            : "/app/resources/Assets/";
    
    // 默认头像路径
    private static final String DEFAULT_AVATAR_PATH = AVATAR_DIR + "avatar_default.webp";
    
    // 头像访问 URL 前缀
    private static final String AVATAR_URL_PREFIX = "/assets/";
    
    // 由于已经移除 TwelveMonkeys 依赖，这里不再通过 ImageIO 检查 WebP 支持
    // WebP 转换交由已配置系统变量的 cwebp 命令行工具来执行
    
    /**
     * 验证文件格式是否允许
     * @param filename 文件名
     * @return 是否允许
     */
    public static boolean isAllowedFormat(String filename) {
        if (filename == null || filename.isEmpty()) {
            return false;
        }
        String extension = getFileExtension(filename).toLowerCase();
        return ALLOWED_EXTENSIONS.contains(extension);
    }
    
    /**
     * 获取文件扩展名
     * @param filename 文件名
     * @return 扩展名（不含点）
     */
    private static String getFileExtension(String filename) {
        int lastDotIndex = filename.lastIndexOf(".");
        if (lastDotIndex == -1) {
            return "";
        }
        return filename.substring(lastDotIndex + 1);
    }
    
    /**
     * 生成唯一的 WebP 文件名
     * @param userId 用户 ID
     * @return 唯一文件名
     */
    public static String generateUniqueFilename(int userId) {
        String timestamp = String.valueOf(System.currentTimeMillis());
        String uuid = UUID.randomUUID().toString().replace("-", "").substring(0, 8);
        return String.format("avatar_%d_%s_%s.webp", userId, timestamp, uuid);
    }
    
    /**
     * 将图片转换为 WebP 格式并保存
     * @param image 原始图片
     * @param filename WebP 文件名
     * @return 保存的完整路径
     * @throws IOException IO 异常
     */
    public static String convertAndSave(BufferedImage image, String filename) throws IOException {
        File dir = new File(AVATAR_DIR);
        if (!dir.exists()) {
            dir.mkdirs();
        }

        File tempPng = new File(AVATAR_DIR + "temp_" + filename.replace(".webp", ".png"));
        ImageIO.write(image, "png", tempPng);

        File outputFile = new File(AVATAR_DIR + filename);

        // 【修改点 2】动态识别 cwebp 路径
        String cwebpPath = System.getProperty("os.name").toLowerCase().contains("win")
                ? "D:/webp/bin/cwebp.exe"
                : "cwebp"; // Linux 下直接使用命令名

        String[] command = {
                cwebpPath,
                "-q", "80",
                tempPng.getAbsolutePath(),
                "-o", outputFile.getAbsolutePath()
        };

        try {
            Process process = new ProcessBuilder(command).start();
            int exitCode = process.waitFor();
            tempPng.delete();

            if (exitCode != 0) {
                throw new IOException("cwebp 转换失败，退出码: " + exitCode);
            }
            return outputFile.getAbsolutePath();
        } catch (InterruptedException e) {
            tempPng.delete();
            Thread.currentThread().interrupt();
            throw new IOException("WebP 转换被中断");
        }
    }

    /**
     * 读取图片文件
     * @param file 文件对象
     * @return BufferedImage 对象
     * @throws IOException IO 异常
     */
    public static BufferedImage readImage(File file) throws IOException {
        return ImageIO.read(file);
    }
    
    /**
     * 从输入流读取图片
     * @param inputStream 输入流
     * @return BufferedImage 对象
     * @throws IOException IO 异常
     */
    public static BufferedImage readImage(java.io.InputStream inputStream) throws IOException {
        return ImageIO.read(inputStream);
    }
    
    /**
     * 判断是否为默认头像
     * @param avatarPath 头像路径
     * @return 是否为默认头像
     */
    public static boolean isDefaultAvatar(String avatarPath) {
        if (avatarPath == null || avatarPath.isEmpty()) {
            return true;
        }
        // 比较路径是否相同（忽略大小写和路径分隔符差异）
        String normalizedPath = avatarPath.replace("\\", "/").toLowerCase().trim();
        String normalizedDefault = DEFAULT_AVATAR_PATH.replace("\\", "/").toLowerCase().trim();
        
        // 宽松匹配：只要包含 avatar_default 就认为是默认头像
        return normalizedPath.contains("avatar_default") || normalizedPath.equals(normalizedDefault);
    }
    
    /**
     * 删除旧头像文件
     * @param avatarPath 头像文件路径
     */
    public static void deleteOldAvatar(String avatarPath) {
        if (avatarPath != null && !avatarPath.isEmpty()) {
            // 如果是默认头像，不删除
            if (isDefaultAvatar(avatarPath)) {
                return;
            }
            
            // 兼容性处理：如果数据库存的是相对 URL (如 /assets/xxx)，需要拼接回物理路径
            String filePath = avatarPath;
            if (avatarPath.startsWith(AVATAR_URL_PREFIX)) {
                String filename = avatarPath.substring(AVATAR_URL_PREFIX.length());
                filePath = AVATAR_DIR + filename;
            }
            
            File oldFile = new File(filePath);
            if (oldFile.exists() && oldFile.isFile()) {
                oldFile.delete();
            }
        }
    }
    
    /**
     * 获取头像访问 URL
     * @param filename 文件名
     * @return 访问 URL
     */
    public static String getAvatarUrl(String filename) {
        return AVATAR_URL_PREFIX + filename;
    }
    
    /**
     * 获取头像存储目录
     * @return 存储目录路径
     */
    public static String getAvatarDir() {
        return AVATAR_DIR;
    }
    
    /**
     * 获取默认头像路径
     * @return 默认头像路径
     */
    public static String getDefaultAvatarPath() {
        return DEFAULT_AVATAR_PATH;
    }
}
