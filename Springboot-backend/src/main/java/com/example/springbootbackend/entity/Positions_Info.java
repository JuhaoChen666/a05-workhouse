package com.example.springbootbackend.entity;

import lombok.Data;

import java.util.Date;
@Data
public class Positions_Info {
    private int id;
    private String name;
    private String responsibility;
    private String salary_junior;
    private String salary_mid;
    private String salary_senior;
    private String salary_expert;
    private String skill_requirements;
    private Date create_time;
    private Date update_time;
}