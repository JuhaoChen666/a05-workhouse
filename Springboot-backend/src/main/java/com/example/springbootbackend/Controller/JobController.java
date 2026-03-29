package com.example.springbootbackend.Controller;

import com.example.springbootbackend.entity.Job;
import com.example.springbootbackend.service.JobService;
import com.example.springbootbackend.utils.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
public class JobController {
    @Autowired
    private JobService jobService;

    @GetMapping("/jobs")
    public Result getAllJobs() {
        return Result.success(jobService.getAllJobs());

    }
    @GetMapping("/jobs/{id}")
    public Result getJobById(@PathVariable Integer id) {
        return Result.success(jobService.getJobById(id));
    }
}
