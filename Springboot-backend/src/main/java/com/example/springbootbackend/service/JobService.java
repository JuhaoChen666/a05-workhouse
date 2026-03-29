package com.example.springbootbackend.service;

import com.example.springbootbackend.entity.Job;
import com.example.springbootbackend.mapper.JobMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class JobService {
    @Autowired
    private JobMapper jobMapper;
    public List<Job> getAllJobs() {
        return jobMapper.getAllJobs();
    }
    public Job getJobById(Integer id) {
        return jobMapper.getJobById(id);
    }
}
