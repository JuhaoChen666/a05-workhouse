package com.example.springbootbackend.entity;

import lombok.Data;
import java.util.Date;

@Data
public class InterviewSession {
    private String sessionId;
    private Integer userId;
    private String resume;
    private String position;
    private String status;
    private String difficulty;
    private String currentTopic;
    private String currentQuestion;
    private Date createdAt;
    private Date updatedAt;
}
