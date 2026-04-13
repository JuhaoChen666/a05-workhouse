package com.example.springbootbackend.mapper;

import com.example.springbootbackend.entity.Resume;
import org.apache.ibatis.annotations.*;
import java.util.List;

@Mapper
public interface ResumeMapper {
    
    // 分页查询简历(支持按user_id模糊查询)
    @Select("<script>" +
            "SELECT id, user_id as userId, filename, local_path as localPath, " +
            "content_text as contentText, uploaded_at as uploadedAt " +
            "FROM resumes " +
            "<where>" +
            "<if test='userId != null'>AND user_id = #{userId}</if>" +
            "</where>" +
            "ORDER BY id ASC " +
            "LIMIT #{offset}, #{pageSize}" +
            "</script>")
    List<Resume> getResumesByPage(@Param("userId") Integer userId, 
                                   @Param("offset") int offset, 
                                   @Param("pageSize") int pageSize);
    
    // 计算总数
    @Select("<script>" +
            "SELECT COUNT(*) FROM resumes " +
            "<where>" +
            "<if test='userId != null'>AND user_id = #{userId}</if>" +
            "</where>" +
            "</script>")
    int countResumes(@Param("userId") Integer userId);
    
    // 根据主键id删除简历
    @Delete("DELETE FROM resumes WHERE id = #{id}")
    int deleteResumeById(Long id);
}
