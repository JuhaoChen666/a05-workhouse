package com.example.springbootbackend.mapper;

import com.example.springbootbackend.entity.Job;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface JobMapper {
    @Select("SELECT * FROM job")
    List<Job> getAllJobs();
    @Select("SELECT * FROM job WHERE id = #{id}")
    Job getJobById(Integer id);
}
