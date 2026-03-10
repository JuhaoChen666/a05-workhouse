package com.example.springbootbackend.entity;

import lombok.Data;

@Data
public class Job {
    private Integer id;
    private String name;
    private String companyName;
    private String companyLogo;
    private String salaryMin;
    private String salaryMax;
    private String jobContent;
    private String type;
}
