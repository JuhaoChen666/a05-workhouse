package com.example.springbootbackend.service;

import com.example.springbootbackend.entity.Resume;
import com.example.springbootbackend.mapper.ResumeMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class ResumeService {
    
    @Autowired
    private ResumeMapper resumeMapper;
    
    // 分页查询简历
    public Map<String, Object> getResumesByPage(Integer userId, int page, int pageSize) {
        int offset = (page - 1) * pageSize;
        List<Resume> resumes = resumeMapper.getResumesByPage(userId, offset, pageSize);
        int total = resumeMapper.countResumes(userId);
        
        Map<String, Object> result = new HashMap<>();
        result.put("list", resumes);
        result.put("total", total);
        result.put("page", page);
        result.put("pageSize", pageSize);
        return result;
    }
    
    // 删除简历
    public int deleteResumeById(Long id) {
        return resumeMapper.deleteResumeById(id);
    }
}
