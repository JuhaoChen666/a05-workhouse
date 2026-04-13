package com.example.springbootbackend.mapper;

import com.example.springbootbackend.entity.InterviewSession;
import org.apache.ibatis.annotations.*;
import java.util.List;

@Mapper
public interface InterviewSessionMapper {
    
    // 分页查询面试会话(支持按user_id查询,支持排序)
    @Select("<script>" +
            "SELECT session_id as sessionId, user_id as userId, resume, position, status, difficulty, " +
            "current_topic as currentTopic, current_question as currentQuestion, " +
            "created_at as createdAt, updated_at as updatedAt " +
            "FROM interview_sessions " +
            "<where>" +
            "<if test='userId != null'>AND user_id = #{userId}</if>" +
            "</where>" +
            "<choose>" +
            "<when test='order != null and order == \"desc\"'>" +
            "ORDER BY " +
            "<choose>" +
            "<when test='sortBy != null and sortBy == \"updated_at\"'>updated_at DESC</when>" +
            "<otherwise>created_at DESC</otherwise>" +
            "</choose>" +
            "</when>" +
            "<otherwise>ORDER BY " +
            "<choose>" +
            "<when test='sortBy != null and sortBy == \"updated_at\"'>updated_at ASC</when>" +
            "<otherwise>created_at ASC</otherwise>" +
            "</choose>" +
            "</otherwise>" +
            "</choose>" +
            "LIMIT #{offset}, #{pageSize}" +
            "</script>")
    List<InterviewSession> getSessionsByPage(@Param("userId") Integer userId,
                                              @Param("offset") int offset,
                                              @Param("pageSize") int pageSize,
                                              @Param("order") String order,
                                              @Param("sortBy") String sortBy);
    
    // 计算总数
    @Select("<script>" +
            "SELECT COUNT(*) FROM interview_sessions " +
            "<where>" +
            "<if test='userId != null'>AND user_id = #{userId}</if>" +
            "</where>" +
            "</script>")
    int countSessions(@Param("userId") Integer userId);
    
    // 根据session_id删除会话
    @Delete("DELETE FROM interview_sessions WHERE session_id = #{sessionId}")
    int deleteSessionById(String sessionId);
}
