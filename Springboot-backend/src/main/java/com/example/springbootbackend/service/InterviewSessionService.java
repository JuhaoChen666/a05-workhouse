package com.example.springbootbackend.service;

import com.example.springbootbackend.entity.InterviewSession;
import com.example.springbootbackend.mapper.InterviewSessionMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class InterviewSessionService {
    
    @Autowired
    private InterviewSessionMapper interviewSessionMapper;
    
    // 分页查询面试会话
    public Map<String, Object> getSessionsByPage(Integer userId, int page, int pageSize, String order, String sortBy) {
        int offset = (page - 1) * pageSize;
        List<InterviewSession> sessions = interviewSessionMapper.getSessionsByPage(userId, offset, pageSize, order, sortBy);
        int total = interviewSessionMapper.countSessions(userId);
        
        Map<String, Object> result = new HashMap<>();
        result.put("list", sessions);
        result.put("total", total);
        result.put("page", page);
        result.put("pageSize", pageSize);
        return result;
    }
    
    // 删除面试会话
    public int deleteSessionById(String sessionId) {
        return interviewSessionMapper.deleteSessionById(sessionId);
    }
}
